"""
Ownership verification logic.

Two methods:
  dns_txt   — query TXT record at _pentashield-verify.<domain>
  file_upload — HTTP GET /.well-known/pentashield.txt on the domain

Both methods look for the verification token in the response.
"""

import asyncio

import dns.asyncresolver
import dns.exception
import httpx

_HTTP_TIMEOUT = 10.0
_DNS_TIMEOUT = 8.0

TXT_SUBDOMAIN = "_pentashield-verify"
WELL_KNOWN_PATH = "/.well-known/pentashield.txt"


async def verify_dns_txt(domain: str, token: str) -> bool:
    """
    Resolve TXT records for _pentashield-verify.<domain> and check
    whether any record contains the expected token.
    """
    qname = f"{TXT_SUBDOMAIN}.{domain}"
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = _DNS_TIMEOUT
    try:
        answers = await resolver.resolve(qname, "TXT")
        for rdata in answers:
            for string in rdata.strings:
                if token.encode() in string or token in string.decode(errors="ignore"):
                    return True
    except (dns.exception.DNSException, asyncio.TimeoutError):
        pass
    return False


async def verify_file_upload(domain: str, token: str) -> bool:
    """
    HTTP GET https://<domain>/.well-known/pentashield.txt and check
    that the response body contains the verification token.
    Falls back to HTTP if HTTPS fails.
    """
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}{WELL_KNOWN_PATH}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
                verify=False,  # some SMB sites have self-signed certs
            ) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and token in resp.text:
                    return True
        except httpx.RequestError:
            continue
    return False


async def check_ownership(domain: str, token: str, method: str) -> bool:
    """Dispatch to the correct verification method."""
    if method == "dns_txt":
        return await verify_dns_txt(domain, token)
    if method == "file_upload":
        return await verify_file_upload(domain, token)
    return False
