import asyncio
import aiohttp
import argparse
import logging
from aiohttp_socks import ProxyConnector
from aiohttp import ClientError
from tqdm.asyncio import tqdm_asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Default target URL for testing proxies
DEFAULT_TEST_URL = "http://httpbin.org/ip"  # This endpoint returns the client's IP address

async def test_proxy(proxy: str, test_url: str):
    """
    Tests a single proxy by attempting to fetch the test URL.
    
    Args:
        proxy (str): The proxy URL.
        test_url (str): The URL to test against.
    
    Returns:
        tuple: (proxy, is_working, status_code or error message)
    """
    try:
        connector = ProxyConnector.from_url(proxy)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(test_url, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"✅ Proxy: {proxy} | Status: {response.status}")
                    return (proxy, True, response.status)
                else:
                    logger.warning(f"⚠️ Proxy: {proxy} | Status: {response.status}")
                    return (proxy, False, response.status)
    except asyncio.TimeoutError:
        logger.error(f"⏰ Proxy: {proxy} | Error: Timeout")
        return (proxy, False, "Timeout")
    except ClientError as e:
        logger.error(f"❌ Proxy: {proxy} | Error: {e}")
        return (proxy, False, str(e))
    except Exception as e:
        logger.error(f"❌ Proxy: {proxy} | Unexpected Error: {e}")
        return (proxy, False, str(e))

async def run_tests(proxies: list, test_url: str, concurrent: int, save_working: bool, output_file: str):
    """
    Runs proxy tests concurrently.
    
    Args:
        proxies (list): List of proxy URLs.
        test_url (str): The URL to test against.
        concurrent (int): Number of concurrent connections.
        save_working (bool): Whether to save working proxies to a file.
        output_file (str): The file to save working proxies.
    
    Returns:
        list: List of tuples containing proxy details.
    """
    sem = asyncio.Semaphore(concurrent)
    results = []

    async def sem_task(proxy):
        async with sem:
            return await test_proxy(proxy, test_url)

    tasks = [sem_task(proxy) for proxy in proxies]
    for f in tqdm_asyncio.as_completed(tasks, total=len(tasks)):
        result = await f
        results.append(result)

    # Save working proxies if required
    if save_working:
        working_proxies = [proxy for proxy, is_working, _ in results if is_working]
        with open(output_file, 'w') as f:
            for proxy in working_proxies:
                f.write(f"{proxy}\n")
        logger.info(f"🔍 Found {len(working_proxies)} working proxies. Saved to {output_file}.")

    return results

def load_proxies(filepath: str) -> list:
    """
    Loads proxies from a file.
    
    Args:
        filepath (str): Path to the proxy file.
    
    Returns:
        list: List of proxy URLs.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            proxies = [line.strip() for line in f if line.strip()]
        logger.info(f"📂 Loaded {len(proxies)} proxies from {filepath}.")
        return proxies
    except FileNotFoundError:
        logger.error(f"❌ Proxy file '{filepath}' not found.")
        return []

def parse_arguments():
    """
    Parses command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Proxy Testing Script")
    parser.add_argument('--proxy_file', type=str, default='proxies.txt', help='Path to the proxy file.')
    parser.add_argument('--test_url', type=str, default=DEFAULT_TEST_URL, help='URL to test proxies against.')
    parser.add_argument('--concurrent', type=int, default=100, help='Number of concurrent proxy tests.')
    parser.add_argument('--save_working', action='store_true', help='Save working proxies to a file.')
    parser.add_argument('--output_file', type=str, default='working_proxies.txt', help='File to save working proxies.')
    return parser.parse_args()

async def main():
    args = parse_arguments()
    proxies = load_proxies(args.proxy_file)
    
    if not proxies:
        logger.error("No proxies to test. Exiting.")
        return
    
    results = await run_tests(
        proxies=proxies,
        test_url=args.test_url,
        concurrent=args.concurrent,
        save_working=args.save_working,
        output_file=args.output_file
    )
    
    # Summary
    total = len(results)
    working = sum(1 for _, is_working, _ in results if is_working)
    failed = total - working
    logger.info("\n📊 Test Summary")
    logger.info(f"Total Proxies Tested: {total}")
    logger.info(f"Working Proxies: {working}")
    logger.info(f"Failed Proxies: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
