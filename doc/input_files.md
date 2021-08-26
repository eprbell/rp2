# Input Files: ODS Spreadsheet and Config File
RP2 reads as input two user-prepared files:
- an ODS-format spreadsheet (containing crypto transactions)
- a JSON config (describing the format of the spreadsheet file).

The user fills the input spreadsheet with crypto transactions using records from exchanges and wallets. The user also writes the config file (or they can start with [crypto_example.config](../config/crypto_example.config) as boilerplate) describing the format and structure of the spreadsheet file:
- meaning of columns,
- cryptocurrencies used,
- exchanges used,
- account owners.

See [crypto_example.ods](../input/crypto_example.ods) and [crypto_example.config](../config/crypto_example.config) to learn more.

## The Config File
The config file tells RP2 how to interpret the input spreadsheet (i.e. what values are contained in what column). The purpose of the config file is input flexibility: unfortunately exchanges don't provide user transaction data in a standardized way, so customizing column positions can be useful. It is in JSON format and contains the following sections (note that optional values can be omitted: sometimes exchanges provide them even though they are redundant):

* **in_header**: JSON object containing [parameter:column_number] value pairs for **IN**-transactions (i.e. transactions that increase cryptocurrency holdings, e.g. buy or earn). Column number 0 corresponds to column A in the input spreadsheet, 1 to B, etc. The in_header parameters are:
  * **timestamp**: time at which the transaction occurred. RP2 can parse most timestamp formats, but timestamps must always include: year, month, day, hour, minute, second and timezone (milliseconds are optional). E.g.: "2020-01-11 11:15:00+00:00".
  * **asset**: which cryptocurrency was transacted (e.g. BTC, ETH, etc.).
  * **exchange**: exchange or wallet on which the transaction occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.).
  * **holder**: exchange account or wallet owner.
  * **transaction_type**: BUY or EARN.
  * **spot_price**: value of 1 unit of the given cryptocurrency at the time the transaction occurred.
  * **crypto_in**: how much of the given cryptocurrency was acquired with the transaction.
  * **usd_fee**: US dollar value of the transaction fees.
  * **usd_in_no_fee** (optional): US dollar value of the transaction without fees. If not provided, RP2 will compute this value automatically.
  * **usd_in_with_fee** (optional): US dollar value of the transaction with fees. If not provided, RP2 will compute this value automatically.
  * **notes** (optional): user-provided description of the transaction.

* **out_header**: JSON object containing [parameter:column_number] value pairs for **OUT**-transactions (i.e. transactions that decrease cryptocurrency holdings, e.g. sell, donate or gift). Column number 0 corresponds to column A in the input spreadsheet, 1 to B, etc. The out_header parameters are:
  * **timestamp**: time at which the transaction occurred. RP2 can parse most timestamp formats, but timestamps must always include: year, month, day, hour, minute, second and timezone (milliseconds are optional). E.g.: "2020-01-11 11:15:00+00:00".
  * **asset**: which cryptocurrency was transacted (e.g. BTC, ETH, etc.).
  * **exchange**: exchange or wallet on which the transaction occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.).
  * **holder**: exchange account or wallet owner.
  * **transaction_type**: DONATE, GIFT or SELL.
  * **spot_price**: value of 1 unit of the given cryptocurrency at the time the transaction occurred.
  * **crypto_out_no_fee**: how much of the given cryptocurrency was sold or sent with the transaction (excluding fees).
  * **crypto_fee**: crypto value of the transaction fees.
  * **crypto_out_with_fee** (optional): how much of the given cryptocurrency was sold or sent with the transaction (excluding fees). If not provided, RP2 will compute this value automatically.
  * **usd_out_no_fee** (optional): US dollar value of the transaction without fees. If not provided, RP2 will compute this value automatically.
  * **usd_fee** (optional): US dollar value of the transactin fees. If not provided, RP2 will compute this value automatically.
   * **notes** (optional): user-provided description of the transaction.

* **intra_header**: JSON object containing [parameter:column_number] value pairs for **INTRA**-transactions (i.e. transactions that don't increase or decrease cryptocurrency holdings, e.g. move across accounts owned by the same person). Column number 0 corresponds to column A in the input spreadsheet, 1 to B, etc. The intra_header parameters are:
  * **timestamp**: time at which the transaction occurred. RP2 can parse most timestamp formats, but timestamps must always include: year, month, day, hour, minute, second and timezone (milliseconds are optional). E.g.: "2020-01-11 11:15:00+00:00".
  * **asset**: which cryptocurrency was transacted (e.g. BTC, ETH, etc.).
  * **from_exchange**: exchange or wallet from which the transfer of cryptocurrency occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.).
  * **from_holder**: owner of the exchange account or wallet from which the transfer of cryptocurrency occurred.
  * **to_exchange**: exchange or wallet to which the transfer of cryptocurrency occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.).
  * **to_holder**: owner of the exchange account or wallet to which the transfer of cryptocurrency occurred.
  * **spot_price**: value of 1 unit of the given cryptocurrency at the time the transaction occurred.
  * **crypto_sent**: how much of the given cryptocurrency was sent with the transaction.
  * **crypto_received**: how much of the given cryptocurrency was received with the transaction.
  * **crypto_fee**: crypto value of the transaction fees.
  * **usd_fee**: US dollar value of the transaction fees.
  * **notes** (optional): user-provided description of the transaction.

* **assets**: JSON array containing a list of valid cryptocurrencies (references to cryptocurrencies not listed here will cause an error).

* **exchanges**: JSON array containing a list of valid exchanges and wallets (references to exchanges or wallets not listed here will cause an error).

* **holders**: JSON array containing a list of valid account and wallet owners (references to holders not listed here will cause an error). Multiple holders can be used by people who file taxes together.

## The Input Spreadsheet
The input spreadsheet is in .ods format and contains one or more sheets. Each sheet is named after one cryptocurrency and contains all transactions denominated in it (allowed cryptocurrencies are defined in the **assets** section of the config file). Each sheet is composed of up to 3 tables:
* The **IN**-table (mandatory) contains transactions describing crypto flowing in (e.g. buy, earn):
  * the first row contains the **IN** keyword in column A
  * the second row is the table header: the meaning of each header cell is defined in the **in_header** section of the config file
  * the following rows describe one **IN**-transaction each
  * the last row contains the **TABLE END** keyword in column A
* The **OUT**-table (optional) contains transactions describing crypto flowing out (e.g. donate, gift, sell):
  * the first row contains the **OUT** keyword in column A
  * the second row is the table header: the meaning of each header cell is defined in the **out_header** section of the config file
  * the following rows describe one **OUT**-transaction each
  * the last row contains the **TABLE END** keyword in column A
* The **INTRA**-table (optional) contains transactions describing crypto moving across accounts owned by the same person (or multiple people filing taxes together):
  * the first row contains the **INTRA** keyword in column A
  * the second row is the table header: the meaning of each header cell is defined in the **intra_header** section of the config file
  * the following rows describe one **INTRA**-transaction each
  * the last row contains the **TABLE END** keyword in column A

Here's an example of an input spreadheet with 2 sheets: one for BTC and one for ETH:
![Input spreadsheet example](images/input_spreadsheet.png)

### **IN**-Transaction Format
**IN**-transactions describe crypto flowing in (e.g. buy, earn) and are contained in the **IN**-table. They have the following parameters (parameter/position mapping is described in the **in_header** section of the config file):
* **timestamp**: time in which the transaction occurred (it must include year, month, day, hour, minute, second and timezone)
* **asset**: cryptocurrency transacted (e.g. BTC, ETH, etc.). It must match the name of the spreadsheet and must match one of the values in the **assets** section of the config file
* **exchange**: exchange or wallet on which the transaction occurred (e.g. Coinbase, BlockFi, etc.). It must match one of the values in the **exchanges** section of the config file
* **holder**: exchange account or wallet owner. It must match one of the values in the **holders** section of the config file
* **transaction_type**: it must be one of BUY or EARN
* **spot_price**: value of 1 unit of the given cryptocurrency at the time the transaction occurred
* **crypto_in**: how much of the given cryptocurrency was acquired with the transaction
* **usd_fee**: US dollar value of the fees
* **usd_in_no_fee** (optional): US dollar value of the transaction without fees. It can be computed from crypto_in and spot_price, but sometime exchanges provide it anyway
* **usd_in_with_fee** (optional): US dollar value of the transaction with fees. It can be computed from crypto_in, spot_price and usd_fee, but sometime exchanges provide it anyway
* **notes** (optional): description of the transaction

### **OUT**-Transaction Format
**OUT**-transactions describe crypto flowing out (e.g. donate, gift, sell) and are contained in the **OUT**-table. They have the following parameters (parameter/position mapping is described in the **out_header** section of the config file):
* **timestamp**: time in which the transaction occurred (it must include year, month, day, hour, minute, second and timezone)
* **asset**: cryptocurrency transacted (e.g. BTC, ETH, etc.). It must match the name of the spreadsheet and one of the values in the **assets** section of the config file
* **exchange**: exchange or wallet on which the transaction occurred (e.g. Coinbase, BlockFi, etc.). It must match one of the values in the **exchanges** section of the config file
* **holder**: exchange account or wallet owner. It must match one of the values in the **holders** section of the config file
* **transaction_type**: it must be one of DONATE, GIFT or SELL
* **spot_price**: value of 1 unit of the given cryptocurrency at the time the transaction occurred
* **crypto_out_no_fee**: how much of the given cryptocurrency was sent with the transaction
* **crypto_fee**: crypto value of the fees,
* **crypto_out_with_fee** (optional): crypto value of the transaction with fees. It can be computed from crypto_out_no_fee and crypto_fee, but sometime exchanges provide it anyway
* **usd_out_no_fee** (optional): USD value of the transaction without fees. It can be computed from crypto_out_no_fee and spot_price, but sometime exchanges provide it anyway
* **usd_fee** (optional): USD value of the fees. It can be computed from crypto_fee and spot_price, but sometime exchanges provide it anyway
* **notes** (optional): description of the transaction

### **INTRA**-Transaction Format
**INTRA**-transactions describe crypto moving across accounts owned by the same person and are contained in the **INTRA**-table. They  have the following parameters (parameter/position mapping is described in the **intra_header** section of the config file):
* **timestamp**: time in which the transaction occurred (it must include year, month, day, hour, minute, second and timezone)
* **asset**: cryptocurrency transacted (e.g. BTC, ETH, etc.). It must match the name of the spreadsheet and one of the values in the **assets** section of the config file
* **from_exchange**: exchange or wallet from which the transfer of crypto occurred (e.g. Coinbase, BlockFi, etc.). It must match one of the values in the **exchanges** section of the config file
* **from_holder**: owner of the exchange account or wallet from which the transfer of crypto occurred. It must match one of the values in the **holders** section of the config file
* **to_exchange**: exchange or wallet to which the transfer of crypto occurred (e.g. Coinbase, BlockFi, etc.). It must match one of the values in the **exchanges** section of the config file
* **to_holder**: owner of the exchange account or wallet to which the transfer of crypto occurred. It must match one of the values in the **holders** section of the config file
* **spot_price** (optional): value of 1 unit of the given cryptocurrency at the time the transaction occurred. Sometimes if fee is zero, exchanges don't provide this value
* **crypto_sent**: how much of the given cryptocurrency was sent with the transaction
* **crypto_received**: how much of the given cryptocurrency was received with the transaction
* **notes** (optional): description of the transaction
