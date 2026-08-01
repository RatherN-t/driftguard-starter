import os

from mistralai.client import Mistral


def main() -> None:
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        raise SystemExit("Set MISTRAL_API_KEY first")
    client = Mistral(api_key=key)
    response = client.models.list()
    for model in response.data:
        print(model.id)


if __name__ == "__main__":
    main()
