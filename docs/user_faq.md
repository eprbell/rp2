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

* **[How to Verify that I Entered Data Correctly in the Input Spreadsheet?](#how-to-verify-that-i-entered-data-correctly-in-the-input-spreadsheet)**
* **[What Is the Timestamp Format?](#what-is-the-timestamp-format)**
* **[What Accounting Methods Are Supported?](#what-accounting-methods-are-supported)**
* **[How to Handle Conversion of a Cryptocurrency to Another?](#how-to-handle-conversion-of-a-cryptocurrency-to-another)**
* **[How to Switch from Another Tax Software to RP2?](#how-to-switch-from-another-tax-software-to-rp2)**
* **[How to Handle Airdrops?](#how-to-handle-airdrops)**
* **[How to Handle Hard Forks?](#how-to-handle-hard-forks)**
* **[How to Handle Income from Mining?](#how-to-handle-income-from-mining)**
* **[How to Handle Income from Staking?](#how-to-handle-income-from-staking)**
* **[How to Handle Futures and Options?](#how-to-handle-futures-and-options)**
* **[How to Handle NFTs?](#how-to-handle-nfts)**
* **[Can I Avoid Writing a Config File from Scratch?](#can-i-avoid-writing-a-config-file-from-scratch)**
* **[Is My Tax Report Browsable?](#is-my-tax-report-browsable)**

* **[Can I Avoid Paying Crypto Taxes?](#can-i-avoid-paying-crypto-taxes)**
* **[Which Resources Can I Use to Learn About Crypto Taxes?](#which-resources-can-i-use-to-learn-about-crypto-taxes)**
* **[Which Crypto Tax Forms to File?](#which-crypto-tax-forms-to-file)**

* **[How to Report a RP2 Bug Without Sharing Personal Information?](#how-to-report-a-rp2-bug-without-sharing-personal-information)**

* **[If I Transfer Cryptocurrency Between Two Accounts I Own, Is the Fee Taxable?](#if-i-transfer-cryptocurrency-between-two-accounts-i-own-is-the-fee-taxable)**
* **[What if I Transfer Cryptocurrency from My Account to My Spouse's Account and We File Taxes Together?](#what-if-i-transfer-cryptocurrency-from-my-account-to-my-spouses-account-and-we-file-taxes-together)**
* **[What Events Are Taxable?](#what-events-are-taxable)**

* **[Who is the Author of RP2?](#who-is-the-author-of-rp2)**
* **[What Does RP2 Mean?](#what-does-rp2-mean)**


## How to Verify that I Entered Data Correctly in the Input Spreadsheet?
In rp2_full_report.ods check the Account Balances table in the tax sheets, and make sure they match the actual balances of your accounts. If not, you probably have an error in the input file or missed some transactions.

## What Is the Timestamp Format?
Timestamp format is [ISO8601](https://en.wikipedia.org/wiki/ISO_8601) (see [examples](https://en.wikipedia.org/wiki/ISO_8601#Combined_date_and_time_representations) of timestamps in this format). Note that RP2 requires full timestamps, including date, time and timezone.

## What Accounting Methods Are Supported?
Currently the [FIFO](https://www.investopedia.com/terms/f/fifo.asp) and [LIFO](https://www.investopedia.com/terms/l/lifo.asp) accounting methods are supported: they can be selected using the `-m` option on the command line.

## How to Handle Conversion of a Cryptocurrency to Another?
Converting from one cryptocurrency to another can be captured in RP2 by splitting the original transaction into two: the first is a SELL-type transaction that describes selling the initial cryptocurrency into fiat. The second one is a BUY-type transaction that describes buying the final cryptocurrency using fiat.

## How to Switch from Another Tax Software to RP2?
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

## How to Handle Airdrops?
Mark the transaction type as AIRDROP. RP2 will collect all such transactions together in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file).

## How to Handle Hard Forks?
Mark the transaction type as HARDFORK. RP2 will collect all such transactions together in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file).

## How to Handle Income from Mining?
Mark the transaction type as MINING. RP2 will collect all such transactions together in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file).

## How to Handle Income from Staking?
Mark the transaction type as STAKING. RP2 will collect all such transactions together in the tax_report_us output. Also read question on [which tax forms to file](#which-crypto-tax-forms-to-file).

## How to Handle Futures and Options?
TBD

## How to Handle NFTs?
RP2 treats NFTs like cryptocurrencies, that is as property. Use a unique asset type for each NFT, both in the config file and in the input spreadsheet: e.g. ETH_BORED_APE_4363. There is debate on whether NFTs should be treated as collectibles instead, but this has not been clarified officially by the IRS yet, to the best of my knowledge. Ask a tax professional for the correct answer in any given year.

## Can I Avoid Writing a Config File from Scratch?
You can use [crypto_example.config](https://github.com/eprbell/rp2/tree/main/config/crypto_example.config) as boilerplate and the [Input Files](https://github.com/eprbell/rp2/tree/main/docs/input_files.md) document as reference.

## Is My Tax Report Browsable?
The rp2_full_report output contains full tax computation details. Part of its contents are hyperlinked to enble browsing: in LibreOffice, CTRL-click (on Mac, Command-click) on a cell to jump to the target:
  * taxable events and acquired lots in the *cryptocurrency* Tax sheet are hyperlinked to their definition line in the *cryptocurrency* In-Out sheet;
  * summary lines in the Summary sheet are hyperlinked to the first line of the given year in the *cryptocurrency* Tax sheet.

## Can I Avoid Paying Crypto Taxes?
No. The IRS has made it clear that [crypto taxes must be paid](https://www.irs.gov/newsroom/irs-reminds-taxpayers-to-report-virtual-currency-transactions).

## Which Resources Can I Use to Learn About Crypto Taxes?
A good starting point is the [Cryptocurrency Tax FAQ](https://www.reddit.com/r/CryptoTax/comments/re6jal/cryptocurrency_tax_faq/) on Reddit. Also read the question on [which tax forms to file](#which-crypto-tax-forms-to-file) and consult with your tax professional.

## Which Crypto Tax Forms to File?
RP2 keeps track of in/out lot relationship, lot fractioning and it computes capital gains and losses, but it doesn't generate the final tax forms. The computed information is written to the tax_report_us output, which intended for tax professionals: all taxable events are grouped in different tabs by type (mining, staking, selling, donating, etc.). Each tax event type has a specific tax treatment: your tax professional can transfer the information from the tax_report_us output tabs to the appropriate forms in any given year.

For additional information on which forms to file, read:
<!-- markdown-link-check-disable -->
* [CoinTracker's summary on this topic](https://www.cointracker.io/blog/what-tax-forms-should-crypto-holders-file).
<!-- markdown-link-check-enable-->
* [IRS Virtual Currency FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions)

Also read the question on [crypto tax resources](#which-resources-can-i-use-to-learn-about-crypto-taxes).

## How to Report a RP2 Bug Without Sharing Personal Information?
See the Reporting Bugs section in the [CONTRIBUTING](../CONTRIBUTING.md#reporting-bugs) document.

## If I Transfer Cryptocurrency Between Two Accounts I Own, Is the Fee Taxable?
Such fees affect the in/out lot relationships, so RP2 keeps track of them (in the "Investment Expenses" tab of the tax_report_us output). Ask your tax professional about how to handle this tab in any given year.

## What if I Transfer Cryptocurrency from My Account to My Spouse's Account and We File Taxes Together?
The names of the people filing taxes together should be added to the holders section of the config file (which is used for validation) and also in the holder column of each transaction in the input file. With this information RP2 generates a joint output. Here's an example in which the people filing together are called Alice and Bob:
* [config/crypto_example.config](https://github.com/eprbell/rp2/tree/main/config/crypto_example.config) (see Alice and Bob in the holders section)
* [input/crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods) (see transactions moving BTC from Bob to Alice in the INTRA table of the BTC tab).

## What Events Are Taxable?
Selling, swapping, donating, mining, staking, earning cryptocurrency are some common taxable events. For an up-to-date list in any given year, ask your tax professional. For additional information on taxable events, read [CoinTracker's summary on crypto taxes](https://www.cointracker.io/blog/what-tax-forms-should-crypto-holders-file).

## Who is the Author of RP2?
The author of RP2 is a Silicon Valley veteran, a software engineer who left the corporate world to become an independent developer and investor. More on eprbell's story [here](https://eprbell.github.io/eprbell//eprbell/status/2021/07/29/the-beginning-of-the-journey.html).

## What Does RP2 Mean?
It's a humorous reference to Warren Buffett’s claim that Bitcoin is [“rat poison squared”](https://www.cnbc.com/2018/05/05/warren-buffett-says-bitcoin-is-probably-rat-poison-squared.html). Other smart people occasionally made [famously](https://www.snopes.com/fact-check/paul-krugman-internets-effect-economy/) [wrong](https://libquotes.com/thomas-edison/quote/lbx5e7q) [remarks](https://en.wikipedia.org/wiki/Robert_Metcalfe#Incorrect_predictions) about technology: I have a feeling Buffett’s quote might end up among those.
