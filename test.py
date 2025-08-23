from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

private_key = "0x83fb9d9f89b89976653eaa1d07ea89df7fe08a29d185edbdd8042c6a1c1e1180"
message_text = "0xbde89394393c7427e4840f468aeb3162282b86f4:100000000000000000000:0"

message = encode_defunct(text=message_text)

signed_message = Account.sign_message(message, private_key=private_key)
print("Signature:", signed_message.signature.hex())

recovered_address = Account.recover_message(message, signature=signed_message.signature)
print("Recovered signer:", recovered_address)


def test_account():
    private_key = "0x83fb9d9f89b89976653eaa1d07ea89df7fe08a29d185edbdd8042c6a1c1e1180"
    acct = Account.from_key(private_key)
    print("Address from COMMUNITY_PRIVATE_KEY:", acct.address)

if __name__=='__main__':
    test_account()