import argparse

from tgtg import TgtgClient


def cli():
    parser = argparse.ArgumentParser(description="Generate tgtg credentials")
    parser.add_argument(
        "email",
        type=str,
        nargs=1,
        help="email of your tgtg account",
    )
    args = parser.parse_args()
    email = args.email[0]
    client = TgtgClient(email=email)
    polling_id = client.get_polling_id()
    print(
        f"You should have received an email to {email}. Open this email on your "
        "computer and click on the link.\n\n"
        "Warning: do not open this link on your phone where you have the app installed. "
        "It will not work"
    )
    credentials = None
    while credentials is None:
        print("\nWhen you done it, press enter")
        input()
        credentials = client.validate_polling_id(polling_id)
        if not credentials:
            print("It looks like you did not clicked on the link in the email.")

    print(credentials)
