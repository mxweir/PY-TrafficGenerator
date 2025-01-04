import asyncio
import aiohttp
import random
import string
import time
import argparse

# Eine Liste von User-Agents, um unterschiedliche Clients zu simulieren
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, wie Gecko) Version/14.0.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, wie Gecko) Chrome/85.0.4183.121 Safari/537.36",
]

def load_proxies_from_file(filepath: str):
    """Lädt Proxys aus einer Datei (jedes Proxy pro Zeile)."""
    proxies = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Falls nicht "http://" oder "https://" Prefix vorhanden ist,
                # kann man es hier hinzufügen (je nach Bedarf)
                if not line.startswith("http"):
                    line = "http://" + line
                proxies.append(line)
    except FileNotFoundError:
        print(f"Proxy-Datei '{filepath}' nicht gefunden. Stelle sicher, dass die Datei existiert.")
    return proxies

def generate_random_cookie():
    """
    Generiert zufällige Cookie-Namen und -Werte, um echte Nutzer zu simulieren.
    Du kannst hier natürlich auch echte Session-Cookies deiner Anwendung einbinden.
    """
    # Zufällige Strings als Platzhalter
    cookie_name = "session_id_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
    cookie_value = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    return {cookie_name: cookie_value}

async def make_request(session: aiohttp.ClientSession, url: str, proxy: str):
    """Führt einen GET-Request auf die Video-URL über die gegebene Proxy-Adresse aus."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    # Cookies für jede Anfrage zufällig generieren
    random_cookies = generate_random_cookie()

    # Zufällige Wartezeit zwischen 0.5 und 3.0 Sekunden
    random_sleep_time = random.uniform(0.5, 3.0)
    
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
            return status_code, text
    except Exception as e:
        return None, str(e)

async def worker(url: str, proxies: list):
    """Ein asynchroner Worker, der nacheinander alle Proxies durchläuft."""
    async with aiohttp.ClientSession() as session:
        results = []
        for proxy in proxies:
            status, data = await make_request(session, url, proxy)
            results.append((proxy, status, data))
        return results

async def main(video_url: str, proxies: list, concurrent_workers: int = 1):
    """
    Startet mehrere asynchrone Workers parallel, sodass
    mehrere Requests gleichzeitig stattfinden können.
    """
    tasks = []
    for _ in range(concurrent_workers):
        tasks.append(asyncio.create_task(worker(video_url, proxies)))

    all_results = await asyncio.gather(*tasks)
    # all_results ist eine Liste von Ergebnislisten, eine pro Worker
    return all_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress-Test-Skript für Video-URLs.")
    parser.add_argument('--video_url', type=str, help='URL des zu testenden Videos')
    parser.add_argument('--proxy_file', type=str, default='proxies.txt', help='Pfad zur Proxy-Datei')
    parser.add_argument('--workers', type=int, default=5, help='Anzahl der parallelen Worker')

    args = parser.parse_args()

    # Proxies aus der Datei laden
    proxies_list = load_proxies_from_file(args.proxy_file)
    
    if not proxies_list:
        print("Keine Proxys geladen. Stelle sicher, dass die Proxy-Datei korrekt ist.")
        exit(1)

    # Video-URL entweder aus Argumenten oder Eingabe
    if args.video_url:
        video_url = args.video_url.strip()
    else:
        video_url = input("Bitte gib die URL des Videos ein, das getestet werden soll: ").strip()
    
    if not video_url:
        print("Keine gültige Video-URL eingegeben.")
        exit(1)

    workers = args.workers

    start_time = time.time()
    results = asyncio.run(main(video_url, proxies_list, workers))
    end_time = time.time()

    # Ergebnisse auswerten
    total_requests = 0
    success_count = 0
    for worker_results in results:
        for proxy, status, data in worker_results:
            total_requests += 1
            if status == 200:
                success_count += 1
            # Nur die ersten Zeichen ausgeben, um das Terminal nicht zu überfluten
            print(f"Proxy: {proxy} | Status: {status} | Fehler/Info: {str(data)[:100]}")

    print("\n--- Zusammenfassung ---")
    print(f"Gesamtanzahl Requests: {total_requests}")
    print(f"Davon mit HTTP-Status 200: {success_count}")
    print(f"Benötigte Zeit: {end_time - start_time:.2f} Sekunden")
