<!--- Copyright 2021 eprbell --->

<!--- Licensed under the Apache License, Version 2.0 (the "License"); --->
<!--- you may not use this file except in compliance with the License. --->
<!--- You may obtain a copy of the License at --->

<!---     http://www.apache.org/licenses/LICENSE-2.0 --->

<!--- Unless required by applicable law or agreed to in writing, software --->
<!--- distributed under the License is distributed on an "AS IS" BASIS, --->
<!--- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. --->
<!--- See the License for the specific language governing permissions and --->
<!--- limitations under the License. --->

# RP2 Frequently Asked Questions (User)

## Table of Contents
* **[General Questions](#general-questions)**
  * [How to Verify that I Entered Data Correctly in the Input Spreadsheet?](#how-to-verify-that-i-entered-data-correctly-in-the-input-spreadsheet)
  * [What Is the Timestamp Format?](#what-is-the-timestamp-format)
  * [What Accounting Methods Are Supported?](#what-accounting-methods-are-supported)
  * [How to Switch from Another Tax Software to RP2?](#how-to-switch-from-another-tax-software-to-rp2)
  * [Can I Avoid Writing a Config File from Scratch?](#can-i-avoid-writing-a-config-file-from-scratch)
  * [Is My Tax Report Browsable?](#is-my-tax-report-browsable)
  * [How to Report a RP2 Bug Without Sharing Personal Information?](#how-to-report-a-rp2-bug-without-sharing-personal-information)
  * [What if I Don't Trust RP2 With my Crypto Data?](#what-if-i-dont-trust-rp2-with-my-crypto-data)
  * [Who is the Author of RP2?](#who-is-the-author-of-rp2)
  * [What Does RP2 Mean?](#what-does-rp2-mean)

* **[Tax Questions](#tax-questions)**
  * [What Events Are Taxable?](#what-events-are-taxable)
  * [Can I Avoid Paying Crypto Taxes?](#can-i-avoid-paying-crypto-taxes)
  * [Which Resources Can I Use to Learn About Crypto Taxes?](#which-resources-can-i-use-to-learn-about-crypto-taxes)
  * [Which Crypto Tax Forms to File?](#which-crypto-tax-forms-to-file)

* **[Tax Scenarios](#tax-scenarios)**
  * [What if I and My Spouse File Taxes Jointly?](#what-if-i-and-my-spouse-file-taxes-jointly)
  * [How to Handle a Transfer of Funds from a Wallet or Exchange to Another?](#how-to-handle-a-transfer-of-funds-from-a-wallet-or-exchange-to-another)
  * [If I Transfer Cryptocurrency Between Two Accounts I Own, Is the Fee Taxable?](#if-i-transfer-cryptocurrency-between-two-accounts-i-own-is-the-fee-taxable)
  * [How to Handle Conversion of a Cryptocurrency to Another?](#how-to-handle-conversion-of-a-cryptocurrency-to-another)
  * [How to Handle Airdrops?](#how-to-handle-airdrops)
  * [How to Handle Donations?](#how-to-handle-donations)
  * [How to Handle Gifts?](#how-to-handle-gifts)
  * [How to Handle Hard Forks?](#how-to-handle-hard-forks)
  * [How to Handle Crypto Interest?](#how-to-handle-crypto-interest)
  * [How to Handle Income from Mining?](#how-to-handle-income-from-mining)
  * [How to Handle Income from Staking?](#how-to-handle-income-from-staking)
  * [How to Handle Income from Crypto Wages?](#how-to-handle-income-from-crypto-wages)
  * [How to Handle Cost-only DeFi Transactions?](#how-to-handle-cost-only-defi-transactions)
  * [How to Handle DeFi Bridging?](#how-to-handle-defi-bridging)
  * [How to Handle DeFi Reflexive Tokens?](#how-to-handle-defi-reflexive-tokens)
  * [How to Handle DeFi Yield from Locked-up Crypto?](#how-to-handle-defi-yield-from-locked-up-crypto)
  * [How to Handle NFTs?](#how-to-handle-nfts)
  * [How to Handle Futures and Options?](#how-to-handle-futures-and-options)

## General Questions

### How to Verify that I Entered Data Correctly in the Input Spreadsheet?
In rp2_full_report.ods check the Account Balances table in the tax sheets, and make sure they match the actual balances of your accounts. If not, you probably have an error in the input file or missed some transactions.

### What Is the Timestamp Format?
Timestamp format is [ISO8601](https://en.wikipedia.org/wiki/ISO_8601) (see [examples](https://en.wikipedia.org/wiki/ISO_8601#Combined_date_and_time_representations) of timestamps in this format). Note that RP2 requires full timestamps, including date, time and timezone.

### What Accounting Methods Are Supported?
Currently the [FIFO](https://www.investopedia.com/terms/f/fifo.asp) and [LIFO](https://www.investopedia.com/terms/l/lifo.asp) accounting methods are supported: they can be selected using the `-m` option on the command line.

### How to Switch from Another Tax Software to RP2?
In other words, how does RP2 handle transactions that were managed by other software in previous years? In this case the user can just leave out from the RP2 input spreadsheet the transactions/lots that were already sold in previous years.

E.g. suppose the user's first year of trading BTC was 2020 and these were their transactions:

<ol type="a">
<li> 2020-2-5: buy 1 BTC</li>
<li> 2020-5-5: buy 2 BTC</li>
<li> 2020-8-1: sell 1.5 BTC</li>
<li> 2021: more transactions...</li>
</ol>

Let's also assume they didn't use RP2 for their 2020 taxes and they used the FIFO accounting method. This means they sold all of lot a) and 0.5 BTC from lot b).

So if they want to start using RP2 for their 2021 taxes, they would just leave out what they already sold and enter the following in the RP2 input spreadsheet:

* 2020-5-5: buy 1.5 BTC</li>
* 2021: more transactions...</li>

This is because lot a), part of lot b) and lot c) are already accounted for in the pre-RP2 system. The Notes column can be useful here: it can be used to describe why lot b) is partial.

Of course the user still needs to keep all the documentation for previous years as well as for the current year. Also they will need to keep the same accounting method they were using previously: to switch accounting method (e.g. from FIFO to LIFO) it's necessary to speak to a tax professional first.

### Can I Avoid Writing a Config File from Scratch?
You can use [crypto_example.config](../config/crypto_example.config) as boilerplate and the [Input Files](input_files.md) document as reference.

### Is My Tax Report Browsable?
The rp2_full_report output contains full tax computation details. Part of its contents are hyperlinked to enable browsing: in LibreOffice, CTRL-click (on Mac, Command-click) on a cell to jump to the target:
  * taxable events and acquired lots in the *cryptocurrency* Tax sheet are hyperlinked to their definition line in the *cryptocurrency* In-Out sheet;
  * summary lines in the Summary sheet are hyperlinked to the first line of the given year in the *cryptocurrency* Tax sheet.

### How to Report a RP2 Bug Without Sharing Personal Information?
See the Reporting Bugs section in the [CONTRIBUTING](../CONTRIBUTING.md#reporting-bugs) document.

### What if I Don't Trust RP2 With my Crypto Data?
In other words how to be sure RP2 is not malware/spyware? After all, Bitcoin's motto is *"don't trust, verify"*. RP2 is open-source and written in Python, so anybody with Python skills can inspect the code anytime: if RP2 tried to do anything untoward (e.g. connecting to a server), someone would likely notice. However if you don't have the time, patience or skill to verify the code and you don't trust others to do so for you, you can still use RP2 in an isolated environment:
- start a fresh virtual machine with your OS of choice;
- install RP2 in the virtual machine;
- isolate the virtual machine: kill networking, shared directories and any other mechanism of outside communication;
- copy your crypto input data to the virtual machine via USB key or other physical medium (because the machine is now isolated);
- run RP2 in the virtual machine;

### Who is the Author of RP2?
The author of RP2 is a Silicon Valley veteran, a software engineer who left the corporate world to become an independent developer and investor. More on eprbell's story [here](https://eprbell.github.io/eprbell//eprbell/status/2021/07/29/the-beginning-of-the-journey.html).

### What Does RP2 Mean?
It's a humorous reference to Warren Buffett’s claim that Bitcoin is [“rat poison squared”](https://www.cnbc.com/2018/05/05/warren-buffett-says-bitcoin-is-probably-rat-poison-squared.html). Other smart people occasionally made [famously](https://www.snopes.com/fact-check/paul-krugman-internets-effect-economy/) [wrong](https://libquotes.com/thomas-edison/quote/lbx5e7q) [remarks](https://en.wikipedia.org/wiki/Robert_Metcalfe#Incorrect_predictions) about technology: I have a feeling Buffett’s quote might end up among those.

## Tax Questions

### What Events Are Taxable?
Selling, swapping, donating, mining, staking, earning cryptocurrency are some common taxable events. For an up-to-date list in any given year, ask your tax professional. For additional information on taxable events read the [Cryptocurrency Tax FAQ](https://www.reddit.com/r/CryptoTax/comments/re6jal/cryptocurrency_tax_faq/) on Reddit and
<!-- markdown-link-check-disable -->
[CoinTracker's summary on crypto taxes](https://www.cointracker.io/blog/what-tax-forms-should-crypto-holders-file).
<!-- markdown-link-check-enable-->

### Can I Avoid Paying Crypto Taxes?
No. The IRS has made it clear that [crypto taxes must be paid](https://www.irs.gov/newsroom/irs-reminds-taxpayers-to-report-virtual-currency-transactions).

### Which Resources Can I Use to Learn About Crypto Taxes?
A good starting point is the [Cryptocurrency Tax FAQ](https://www.reddit.com/r/CryptoTax/comments/re6jal/cryptocurrency_tax_faq/) on Reddit. Also read the question on [which tax forms to file](#which-crypto-tax-forms-to-file) and consult with your tax professional.

### Which Crypto Tax Forms to File?
RP2 keeps track of in/out lot relationship, lot fractioning and it computes capital gains and losses, but it doesn't generate the final tax forms. The computed information is written to the tax_report_us output, which is intended for tax professionals: all taxable events are grouped in different tabs by type (mining, staking, selling, donating, etc.). Each tax event type has a specific tax treatment: your tax professional can transfer the information from the tax_report_us output tabs to the appropriate forms in any given year.

For additional information on which forms to file read:
<!-- markdown-link-check-disable -->
* [CoinTracker's summary on this topic](https://www.cointracker.io/blog/what-tax-forms-should-crypto-holders-file).
<!-- markdown-link-check-enable-->
* [IRS Virtual Currency FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions)

Also read the question on [crypto tax resources](#which-resources-can-i-use-to-learn-about-crypto-taxes).

## Tax Scenarios

### What if I and My Spouse File Taxes Jointly?
The names of the people filing taxes jointly should be added to the holders section of the config file (which is used for validation) and also in the holder column of each transaction in the input file. With this information RP2 generates a joint output. Here's an example in which the people filing jointly are called Alice and Bob:
* [config/crypto_example.config](../config/crypto_example.config) (see Alice and Bob in the holders section)
* [input/crypto_example.ods](../input/crypto_example.ods) (see transactions moving BTC from Bob to Alice in the INTRA table of the BTC tab).

See the [input files](input_files.md) section of the documentation for format details.

### How to Handle a Transfer of Funds from a Wallet or Exchange to Another?
If the both the source and destination accounts belong to the same owner (or to [people filing jointly](#what-if-i-and-my-spouse-file-taxes-jointly)), use an INTRA transaction. Otherwise, use an OUT transaction. See the [input files](input_files.md) section of the documentation for format details.

### If I Transfer Cryptocurrency Between Two Accounts I Own, Is the Fee Taxable?
Such fees affect the in/out lot relationships, so RP2 keeps track of them (in the "Investment Expenses" tab of the tax_report_us output). Ask your tax professional about how to handle this tab in any given year.

### How to Handle Conversion of a Cryptocurrency to Another?
Converting from one cryptocurrency to another can be captured in RP2 by splitting the original transaction into two: the first is a SELL-type transaction that describes selling the initial cryptocurrency into fiat. The second one is a BUY-type transaction that describes buying the final cryptocurrency using fiat. See the [input files](input_files.md) section of the documentation for format details.

### How to Handle Airdrops?
Use an IN transaction and mark the transaction type as AIRDROP. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Donations?
Use an IN transaction (if receiving crypto) or OUT transaction (if giving crypto) and mark the transaction type as DONATION. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Gifts?
Use an IN transaction (if receiving crypto) or OUT transaction (if giving crypto) and mark the transaction type as GIFT. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Hard Forks?
Use an IN transaction and mark the transaction type as HARDFORK. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Crypto Interest?
Use an IN transaction and mark the transaction type as INTEREST. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Income from Mining?
Use an IN transaction and mark the transaction type as MINING. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Income from Staking?
Use an IN transaction and mark the transaction type as STAKING. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Income from Crypto Wages?
Use an IN transaction and mark the transaction type as WAGES. RP2 will collect gain/loss computations for all such transactions in a tab in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file) and see the [input files](input_files.md) section of the documentation for format details.

### How to Handle Cost-only DeFi Transactions?
DeFi opens up new scenarios that have their own tax implications. For example:
* a transaction calls a smart contract function that executes and costs some ETH or BNB;
* investment in a DEFI project where a percentage of invested tokens are "burned";
* send 100 CAKE from one BSC wallet to another then the fees are paid in BNB not CAKE.

In RP2 such native crypto costs can be captured via an [OUT/SELL transaction](input_files.md#out-transaction-table-format) with either:
* `crypto_out`=*100%_of_cost*, `crypto_fee`=*0%_of_cost* or
* `crypto_out`=*0%_of_cost*, `crypto_fee`=*100%_of_cost*.

Remember to use the Notes field to provide context about the nature of the transaction. See the [input files](input_files.md) section of the documentation for format details.

### How to Handle DeFi Bridging?
There is an ongoing debate on how to manage DeFi bridging from a tax perspective. I don't have a definitive answer to the question, but RP2 has expressive primitives that can be used to describe many tax scenarios in different ways. Check this [RP2 issue](https://github.com/eprbell/rp2/issues/4) for a brainstorming on the subject and consult your tax professional. If you have additional insight on this, feel free to contribute to the issue or open a new one.

### How to Handle DeFi Reflexive Tokens?
There is an ongoing debate on how to manage DeFi reflexive tokens from a tax perspective. I don't have a definitive answer to the question, but RP2 has expressive primitives that can be used to describe many tax scenarios in different ways. Check this [RP2 issue](https://github.com/eprbell/rp2/issues/4) for a brainstorming on DeFi and consult your tax professional. If you have additional insight on this, feel free to contribute to the issue or open a new one.

### How to Handle DeFi Yield from Locked-up Crypto?
DeFi opens up new scenarios that have their own tax implications. For example:
* lock 100 DRIP forever and then get 1 DRIP per day back for a max of 365 days;
* buy a "node" that consumes 10 STRONG, but after that the node produces 0.1 STRONG per day, forever.

There is an ongoing debate on how to capture this scenario from a tax perspective: how is the locked-forever crypto handled? Are the first yields considered "recovered" capital and the following ones staking? I don't have a definitive answer to the question, but RP2 has expressive primitives that can be used to describe many tax scenarios in different ways. Check this [RP2 issue](https://github.com/eprbell/rp2/issues/4) for a brainstorming on the subject and consult your tax professional. If you have additional insight on this, feel free to contribute to the issue or open a new one.

### How to Handle NFTs?
RP2 treats NFTs like cryptocurrencies, that is as property. Use a unique asset type for each NFT, both in the config file and in the input spreadsheet (see the [input files](input_files.md) section of the documentation for format details): e.g. ETH_BORED_APE_4363. There is debate on whether NFTs should be treated as collectibles instead, but this has not been clarified officially by the IRS yet, to the best of my knowledge. Ask a tax professional for the correct answer in any given year.

### How to Handle Futures and Options?
Calling for help on this question: if you have insight on this please open an issue or a PR.
