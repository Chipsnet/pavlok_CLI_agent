import argparse
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def call(stimulus_type: str, stimulus_value: int):
    url = "https://api.pavlok.com/api/v5/stimulus/send"
    api_key = os.getenv("PAVLOK_API_KEY")
    if not api_key:
        raise SystemExit("PAVLOK_API_KEY is not set. Add it to .env or the environment.")

    payload = {
        "stimulus": {
            "stimulusType": stimulus_type,
            "stimulusValue": stimulus_value,
        }
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)


def main():
    parser = argparse.ArgumentParser(
        description="Send a Pavlok stimulus via the API.",
    )
    parser.add_argument("stimulusType", help="Type of stimulus to send.")
    parser.add_argument("stimulusValue", type=int, help="Stimulus value as an integer.")
    args = parser.parse_args()

    call(args.stimulusType, args.stimulusValue)


if __name__ == "__main__":
    main()
