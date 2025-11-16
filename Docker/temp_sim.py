import random
import time

def read_temp_data():
    return {
        "temperature": round(random.uniform(10,25), )
    }

if __name__ == "__main__":
    while True:
        print(read_temp_data())
        time.sleep(1.0)