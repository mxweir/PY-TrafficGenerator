import asyncio
import aiohttp
import random
import string
import time
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

# A list of User-Agents to simulate different clients
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/14.0.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
]

def load_proxies_from_file(filepath: str) -> list:
    """Loads proxies from a file (one proxy per line)."""
    proxies = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # If the line does not start with "http://", "https://", "socks4://", or "socks5://", add "http://"
                if not line.startswith(("http://", "https://", "socks4://", "socks5://")):
                    line = "http://" + line
                proxies.append(line)
        logger.info(f"📂 Loaded {len(proxies)} proxies from {filepath}.")
    except FileNotFoundError:
        logger.error(f"❌ Proxy file '{filepath}' not found. Please ensure the file exists.")
    return proxies

def generate_random_cookie() -> dict:
    """
    Generates random cookie names and values to simulate real users.
    You can, of course, also include actual session cookies from your application here.
    """
    # Random strings as placeholders
    cookie_name = "session_id_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
    cookie_value = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    return {cookie_name: cookie_value}

async def make_request(session: aiohttp.ClientSession, url: str, proxy: str, retries: int = 3) -> tuple:
    """Performs a GET request to the video URL using the given proxy address with retry logic."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    # Generate random cookies for each request
    random_cookies = generate_random_cookie()

    # Random delay between 0.5 and 3.0 seconds to mimic real user behavior
    random_sleep_time = random.uniform(0.5, 3.0)

    for attempt in range(1, retries + 1):
        try:
            await asyncio.sleep(random_sleep_time)

            async with session.get(
                url,
                headers=headers,
                proxy=proxy,
                timeout=10,
                cookies=random_cookies
            ) as response:
                status_code = response.status
                text = await response.text()
                if status_code == 200:
                    logger.info(f"✅ Proxy: {proxy} | Status: {status_code}")
                else:
                    logger.warning(f"⚠️ Proxy: {proxy} | Status: {status_code} | Response: {text[:100]}")
                return (proxy, status_code, text)
        except asyncio.TimeoutError:
            logger.error(f"⏰ Proxy: {proxy} | Attempt {attempt} failed with error: Timeout")
        except ClientError as e:
            logger.error(f"❌ Proxy: {proxy} | Attempt {attempt} failed with error: {e}")
        except Exception as e:
            logger.exception(f"❌ Proxy: {proxy} | Attempt {attempt} failed with unexpected error: {e}")
        
        if attempt < retries:
            logger.info(f"🔄 Proxy: {proxy} | Retrying... ({attempt}/{retries})")
            await asyncio.sleep(1)  # Wait before retrying
        else:
            logger.error(f"❌ Proxy: {proxy} | All {retries} attempts failed.")
            return (proxy, None, str(e) if 'e' in locals() else "Unknown Error")

async def worker(name: int, url: str, proxies: list, semaphore: asyncio.Semaphore) -> list:
    """An asynchronous worker that processes its assigned proxies."""
    results = []
    async with semaphore:
        connector = None  # No default connector; handled per request via proxy
        async with aiohttp.ClientSession(connector=connector) as session:
            for proxy in proxies:
                result = await make_request(session, url, proxy)
                results.append(result)
    return results

async def main(video_url: str, proxies: list, concurrent_workers: int):
    """
    Launches multiple asynchronous workers in parallel so that
    multiple requests can occur simultaneously.
    """
    if concurrent_workers < 1:
        concurrent_workers = 1

    # Split proxies among workers
    chunk_size = max(1, len(proxies) // concurrent_workers)
    proxy_chunks = [proxies[i:i + chunk_size] for i in range(0, len(proxies), chunk_size)]

    # If there are more workers than proxy chunks, adjust the number of workers
    actual_workers = min(concurrent_workers, len(proxy_chunks))
    logger.info(f"🔧 Distributing {len(proxies)} proxies among {actual_workers} workers.")

    # Semaphore to limit concurrent workers
    semaphore = asyncio.Semaphore(actual_workers)

    tasks = []
    for idx, proxy_chunk in enumerate(proxy_chunks, 1):
        logger.info(f"🚀 Starting worker {idx}/{actual_workers} with {len(proxy_chunk)} proxies.")
        tasks.append(asyncio.create_task(worker(idx, video_url, proxy_chunk, semaphore)))

    all_results = await asyncio.gather(*tasks)
    # Flatten the list of lists
    flat_results = [item for sublist in all_results for item in sublist]
    return flat_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress testing script for video URLs.")
    parser.add_argument('--video_url', type=str, required=True, help='URL of the video to be tested')
    parser.add_argument('--proxy_file', type=str, default='proxies.txt', help='Path to the proxy file')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers')

    args = parser.parse_args()

    # Load proxies from the file
    proxies_list = load_proxies_from_file(args.proxy_file)

    if not proxies_list:
        logger.error("❌ No proxies loaded. Please ensure the proxy file is correct and contains valid proxies.")
        exit(1)

    # Video URL
    video_url = args.video_url.strip()

    if not video_url:
        logger.error("❌ No valid video URL entered.")
        exit(1)

    workers = args.workers
    start_time = time.time()

    try:
        results = asyncio.run(main(video_url, proxies_list, workers))
    except Exception as e:
        logger.exception(f"❌ An error occurred during the stress test: {e}")
        exit(1)

    end_time = time.time()

    # Evaluate results
    total_requests = len(results)
    success_count = sum(1 for _, status, _ in results if status == 200)
    failure_count = total_requests - success_count

    logger.info("\n📊 --- Summary ---")
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"Successful Requests (HTTP 200): {success_count}")
    logger.info(f"Failed Requests: {failure_count}")
    logger.info(f"Time Taken: {end_time - start_time:.2f} seconds")
