# Copyright 2021 eprbell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from importlib import import_module
from types import ModuleType

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.rp2_error import RP2TypeError, RP2ValueError

ACCOUNTING_METHOD_PACKAGE = "rp2.plugin.accounting_method"


# Loads the accounting method plugin with the given name: the name of its module in rp2.plugin.accounting_method (e.g. "fifo" loads
# rp2.plugin.accounting_method.fifo). It's the only place that turns a method name into a method object, so a name from the configuration
# file always gives the same method: the command line (-m and accounting_methods) and the per-wallet tax engine (unused basis allocation)
# both use it. Raises RP2ValueError if there is no such plugin.
def load_accounting_method(accounting_method_name: str) -> AbstractAccountingMethod:
    if not isinstance(accounting_method_name, str) or not accounting_method_name.strip():
        raise RP2TypeError(f"Parameter 'accounting_method_name' is not a non-empty string: {repr(accounting_method_name)}")
    try:
        accounting_method_module: ModuleType = import_module(f"{ACCOUNTING_METHOD_PACKAGE}.{accounting_method_name}", package=ACCOUNTING_METHOD_PACKAGE)
    except ModuleNotFoundError:
        raise RP2ValueError(f"Invalid/unsupported accounting method: {accounting_method_name}") from None
    if not hasattr(accounting_method_module, "AccountingMethod"):
        raise RP2ValueError(f"Accounting method plugin {accounting_method_name} doesn't have an AccountingMethod class")
    result = accounting_method_module.AccountingMethod()
    if not isinstance(result, AbstractAccountingMethod):
        raise RP2TypeError(f"Accounting method plugin {accounting_method_name}: AccountingMethod is not a subclass of AbstractAccountingMethod")
    return result
