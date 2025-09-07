import asyncio
import sys
import time

import httpx


async def one(client, url):
    t0 = time.perf_counter()
    r = await client.get(url)
    r.raise_for_status()
    return (time.perf_counter() - t0) * 1000.0


async def run(url, n=100, concurrency=20):
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=5.0) as client:

        async def wrapped():
            async with sem:
                return await one(client, url)

        lat = await asyncio.gather(*[wrapped() for _ in range(n)])
    lat.sort()

    def pct(p):
        k = (len(lat) - 1) * p / 100.0
        i = int(k)
        f = k - i
        return lat[i] * (1 - f) + lat[min(i + 1, len(lat) - 1)] * f

    print(f"n={n} conc={concurrency}")
    print(f"P50={pct(50):.1f}ms  P95={pct(95):.1f}ms  P99={pct(99):.1f}ms  max={lat[-1]:.1f}ms")


if __name__ == "__main__":
    url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "http://localhost:8001/gyms/search?pref=chiba&city=funabashi&per_page=10"
    )
    asyncio.run(run(url))
