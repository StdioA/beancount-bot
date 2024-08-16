import requests
from vec_db import query_by_embedding
from bean_utils.txs_query import embedding
import conf


# flake8: noqa
_PROMPT_TEMPLATE = """The user is using Beancount for bookkeeping. For simplicity, there is currently a set of accounting grammar that is converted by a program into complete transaction records. The format of the grammar is `<price> <outflow_account> [<inflow_account>] <payee> [<description>] [#<tag1> [#<tag2>] ...]`, where the inflow and outflow accounts are subject to fuzzy matching.

For example：`5 微信 餐饮 麦当劳 午饭 #tag1 #another` will be converted to the following record:

2024-08-16 * "麦当劳" "午饭" #tag1 #another
  Assets:Checking:微信支付:Deposit            -5.00 CNY
  Expenses:Daily:餐饮

However, user input is not accurate enough and may be missing some information, maybe it's payee or description, or one or all of accounts.  
I will provide you with several reference sets, hoping that you can combine the reference information with the user's input to piece together a complete accounting record.  
The user's input will be given by user.

You can do it as following:
1. Try your best to find the correct place for every given word from the reference sets, but not the accounting grammar.  
2. If any information is missing, you should take the information from the reference sets and try to fill the missing part.  
3. Only output the complete accounting record, without any quotes or delemeters.

Finally, there are some reference information.
Today's date: {date}
Reference account names are: `{accounts}`
Reference records are separated by dash delimiter:
{reference_records}
"""


def complete_rag(args, date, accounts):
    # Remove the numeric value at first
    stripped_input = " ".join(args[1:])

    candidates = conf.config.embedding.candidates or 3
    rag_config = conf.config.rag

    match = query_by_embedding(embedding([stripped_input])[0][0]["embedding"], stripped_input, candidates)
    reference_records = "\n------\n".join([x["content"] for x in match])
    prompt = _PROMPT_TEMPLATE.format(date=date, reference_records=reference_records, accounts=accounts)
    payload = {
        "model": rag_config.model,
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": " ".join(args),
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {rag_config.api_key}",
    }
    response = requests.post(rag_config.api_url, json=payload, headers=headers)
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return content.strip("`\n")
