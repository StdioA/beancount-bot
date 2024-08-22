# Beancount Bot
[中文文档](README_zh.md)

A Beancount bot that allows for quick manual recording of simple transactions via IM software.

* Supporting Telegram and Mattermost as frontend
* Supports basic account recording:
    * Supports basic grammar matching: `{amount} {from_account} {to_account} "{payee}" "{narration}" [{#tag1} {#tag2}]`
    * If the same payee already exists in the current data, the to_account can be omitted.
    * After matching failure, it can attempt record matching from a vector database or complete information through RAG.
* Interval expenditure statistics: `/expense 2024-08`
* Interval account change statistics: `/bill 2024-08`
* After submitting a new record, it will automatically reload the ledger entry cache.

## Running
### Running with Docker
Copy `config.yaml` from [`config.yaml.example`](config.yaml.example) to your ledger directory and modify its contents as needed (refer to comments in the configuration file for specific meanings).

Then download [compose.yaml](compose.yaml) to the ledger directory. If you want to run a Mattermost bot, modify the `command` value and configure `ports` to expose ports for receiving Webhooks.

Finally, run `docker compose up -d`.

### Running via Command Line
Install basic dependencies firstly: `pip install -r requirements.txt`

If your device supports [sqlite-vec](https://github.com/asg017/sqlite-vec), you can additionally install the vector database component `pip install sqlite-vec==0.1.1` and use sqlite as the database; if `sqlite-vec` is not installed, the bot will use json to store vector data and numpy for vector calculations.

To use Telegram as a frontend, install `python-telegram-bot`: `pip install python-telegram-bot==21.4`;  
To use Mattermost as a frontend, install `mmpy-bot`: `pip install mmpy-bot==2.1.4`.

Finally, run the bot: `python main.py telegram -c config.yaml` or `python main.py mattermost -c config.yaml`.

## Usage
If Telegram is used as the frontend, you can configure the bot command list in advance at [BotFather](https://telegram.me/BotFather):

```
start - ping
bill - query account changes
expense - query expenses
clone - duplicate transaction
build - rebuild vector database
```

Subsequent operations will be exemplified using Telegram as the frontend. If Mattermost is used as the frontend, any differences in usage will be noted separately.

### Basic Accounting
Basic Syntax: `{Amount} {Outgoing Account} [{Incoming Account}] "{Payee}" "{Narration}" [{#tag1} {#tag2} ...]`, where outgoing and incoming accounts support partial matching.  
If the same payee already exists in the current data, the incoming account can be omitted (`{Amount} {Outgoing Account} "{Payee}" "{Narration}"`);  
If all matching rules fail, it will attempt to match the closest entry from an existing vector database based on available information, updating its amount and date. This method supports accounting formats like `{Amount} {Payee}` or `{Amount} {Narration}` among others.

After input, the bot will complete the transaction details and output them for user confirmation or cancellation of changes.

<img src="example/basic_record.png" alt="basic example of accounting" width="500" height="350">

### Other Commands
* `/build`: Rebuild the vector database.
* `/expense {range} {level}`: Summarize account expenses within a specified time period, supports combination by account level.
    * Mattermost command format follows CLI style: `expense [-l {level}] [{range}]`
    * Default level is 2, default range is yesterday.
* `/bill {range} {level}`: Summarize account changes within a specified time period, supports combination by account level.
    * Mattermost command: `bill [-l {level}] [{range}]`
    * Default parameter settings are the same as above.
* `/clone`: Reply to an existing transaction with this command to generate a new transaction with today's date.
    * Due to Mattermost's limited support for message referencing, cloning is temporarily unsupported; future updates may consider using reactions or other methods to achieve this functionality.

## Roadmap
- [x] Support outputting multiple alternatives when matching with vector database (to compensate for accuracy deficiencies)
- [x] Clone transaction
- [ ] Withdraw transaction
- [x] Docker support
- [ ] Unit tests
- [ ] Web-based Chat UI
- [x] RAG (More precise element replacement through LLM, such as automatically changing "lunch" to "dinner", or automatically updating account changes, etc.)
- [ ] Support incremental construction of vector databases (If using OpenAI's `text-embedding-3-large`, currently building a database consisting of 1000 transactions costs approximately $0.003, and most providers of embedding do not charge for the embedding function, so the priority is not high)

## Reference
[开始使用 Beancount - Telegram bot](https://blog.stdioa.com/2020/09/using-beancount/#telegram-bot)
