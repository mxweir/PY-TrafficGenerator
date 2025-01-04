import asyncio
import aiohttp
import random
import string
import time
import argparse
from aiohttp_socks import ProxyConnector, ProxyType

# A list of User-Agents to simulate different clients
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/14.0.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
]

def load_proxies_from_file(filepath: str):
    """Loads proxies from a file (one proxy per line)."""
    proxies = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # If the line does not start with "http://" or "https://", add it here (as needed)
                if not line.startswith(("http://", "https://", "socks4://", "socks5://")):
                    # Default to HTTP proxy if no scheme is provided
                    line = "http://" + line
                proxies.append(line)
    except FileNotFoundError:
        print(f"Proxy file '{filepath}' not found. Please ensure the file exists.")
    return proxies

def generate_random_cookie():
    """
    Generates random cookie names and values to simulate real users.
    You can, of course, also include actual session cookies from your application here.
    """
    # Random strings as placeholders
    cookie_name = "session_id_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
    cookie_value = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    return {cookie_name: cookie_value}

async def make_request(url: str, proxy: str):
    """Performs a GET request to the video URL using the given proxy address."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    # Generate random cookies for each request
    random_cookies = generate_random_cookie()

    # Random delay between 0.5 and 3.0 seconds
    random_sleep_time = random.uniform(0.5, 3.0)
    
    try:
        await asyncio.sleep(random_sleep_time)
        
        # Determine the proxy type based on the proxy URL scheme
        if proxy.startswith("socks5://"):
            proxy_type = ProxyType.SOCKS5
        elif proxy.startswith("socks4://"):
            proxy_type = ProxyType.SOCKS4
        elif proxy.startswith("https://"):
            proxy_type = ProxyType.HTTP
        else:
            proxy_type = ProxyType.HTTP  # Default to HTTP for "http://"

        # Create a ProxyConnector based on the proxy type
        connector = ProxyConnector.from_url(proxy, proxy_type=proxy_type)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url,
                headers=headers,
                timeout=10,
                cookies=random_cookies
            ) as response:
                status_code = response.status
                text = await response.text()
                return status_code, text
    except Exception as e:
        return None, str(e)

async def worker(url: str, proxies: list):
    """An asynchronous worker that sequentially processes all proxies."""
    results = []
    for proxy in proxies:
        status, data = await make_request(url, proxy)
        results.append((proxy, status, data))
    return results

async def main(video_url: str, proxies: list, concurrent_workers: int = 1):
    """
    Launches multiple asynchronous workers in parallel so that
    multiple requests can occur simultaneously.
    """
    tasks = []
    for _ in range(concurrent_workers):
        tasks.append(asyncio.create_task(worker(video_url, proxies)))

    all_results = await asyncio.gather(*tasks)
    # all_results is a list of result lists, one per worker
    return all_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress testing script for video URLs.")
    parser.add_argument('--video_url', type=str, help='URL of the video to be tested')
    parser.add_argument('--proxy_file', type=str, default='proxies.txt', help='Path to the proxy file')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers')

    args = parser.parse_args()

    # Load proxies from the file
    proxies_list = load_proxies_from_file(args.proxy_file)
    
    if not proxies_list:
        print("No proxies loaded. Please ensure the proxy file is correct.")
        exit(1)

    # Video URL either from arguments or input
    if args.video_url:
        video_url = args.video_url.strip()
    else:
        video_url = input("Please enter the URL of the video to test: ").strip()
    
    if not video_url:
        print("No valid video URL entered.")
        exit(1)

    workers = args.workers

    start_time = time.time()
    results = asyncio.run(main(video_url, proxies_list, workers))
    end_time = time.time()

    # Evaluate results
    total_requests = 0
    success_count = 0
    for worker_results in results:
        for proxy, status, data in worker_results:
            total_requests += 1
            if status == 200:
                success_count += 1
            # Print only the first few characters to avoid flooding the terminal
            print(f"Proxy: {proxy} | Status: {status} | Error/Info: {str(data)[:100]}")

    print("\n--- Summary ---")
    print(f"Total Requests: {total_requests}")
    print(f"Successful Requests (HTTP 200): {success_count}")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
