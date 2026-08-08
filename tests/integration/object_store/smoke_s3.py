import datetime
import hashlib
import hmac
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


SERVICE = "s3"


def main():
    endpoint = require_env("GARAGE_S3_ENDPOINT").rstrip("/")
    bucket = require_env("GARAGE_BUCKET")
    access_key = require_env("GARAGE_KEY_ID")
    secret_key = require_env("GARAGE_SECRET_KEY")
    region = os.environ.get("GARAGE_S3_REGION", "garage")

    object_key = "smoke/s3-smoke.txt"
    body = b"garage s3 smoke ok\n"
    expected_sha256 = hashlib.sha256(body).hexdigest()

    request("PUT", endpoint, bucket, object_key, access_key, secret_key, region, body=body)
    fetched = request("GET", endpoint, bucket, object_key, access_key, secret_key, region)
    assert hashlib.sha256(fetched).hexdigest() == expected_sha256

    listing = request(
        "GET",
        endpoint,
        bucket,
        "",
        access_key,
        secret_key,
        region,
        query={"list-type": "2", "prefix": "smoke/"},
    )
    keys = {element.text for element in ET.fromstring(listing).iter() if element.tag.endswith("Key")}
    assert object_key in keys

    request("DELETE", endpoint, bucket, object_key, access_key, secret_key, region)
    try:
        request("GET", endpoint, bucket, object_key, access_key, secret_key, region)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("deleted object was still readable")


def request(method, endpoint, bucket, key, access_key, secret_key, region, body=b"", query=None):
    query = query or {}
    path = f"/{bucket}"
    if key:
        path += "/" + "/".join(urllib.parse.quote(part, safe="") for part in key.split("/"))
    encoded_query = urllib.parse.urlencode(sorted(query.items()))
    url = f"{endpoint}{path}"
    if encoded_query:
        url = f"{url}?{encoded_query}"

    payload_hash = hashlib.sha256(body).hexdigest()
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    date = timestamp[:8]
    parsed_endpoint = urllib.parse.urlparse(endpoint)
    host = parsed_endpoint.netloc
    headers = {
        "Host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": timestamp,
    }
    authorization = sign(method, path, encoded_query, headers, payload_hash, access_key, secret_key, region, date)
    headers["Authorization"] = authorization

    req = urllib.request.Request(url, data=body if method in {"PUT", "POST"} else None, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read()


def sign(method, path, query, headers, payload_hash, access_key, secret_key, region, date):
    canonical_headers = "".join(f"{name.lower()}:{headers[name].strip()}\n" for name in sorted(headers, key=str.lower))
    signed_headers = ";".join(name.lower() for name in sorted(headers, key=str.lower))
    canonical_request = "\n".join(
        [
            method,
            path,
            query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date}/{region}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            headers["x-amz-date"],
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    signing_key = derive_signing_key(secret_key, date, region)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return (
        "AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


def derive_signing_key(secret_key, date, region):
    date_key = hmac.new(f"AWS4{secret_key}".encode(), date.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, region.encode(), hashlib.sha256).digest()
    service_key = hmac.new(region_key, SERVICE.encode(), hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


if __name__ == "__main__":
    main()
