# import asyncio
#
# async def main():
#     print('Start')
#     await asyncio.sleep(1)
#     print('Finish')
#
# asyncio.run(main())

import asyncio

async def fetch_data():
    print("Starting request...")
    await asyncio.sleep(3)  # Simulates waiting for a network response
    print("Request finished")

async def main():
    task = asyncio.create_task(fetch_data())

    print("Doing other work...")
    await asyncio.sleep(1)
    print("Still doing other work...")

    await task

asyncio.run(main())




