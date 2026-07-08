"""Selecția implementării adaptorului: ODOO_ADAPTER=xmlrpc|fake (plan §5)."""

from .. import config
from .contract import OdooAdapter

_adapter: OdooAdapter | None = None


def get_adapter() -> OdooAdapter:
    global _adapter
    if _adapter is None:
        if config.ODOO_ADAPTER == "xmlrpc":
            from .odoo_xmlrpc import XmlRpcOdooAdapter

            _adapter = XmlRpcOdooAdapter()
        else:
            from .fake import FakeOdooAdapter

            _adapter = FakeOdooAdapter()
    return _adapter


def set_adapter(adapter: OdooAdapter | None) -> None:
    """Pentru teste: injectează o instanță (sau None pentru re-init)."""
    global _adapter
    _adapter = adapter
