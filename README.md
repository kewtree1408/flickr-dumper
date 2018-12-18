## Flickr-dumper

It is a small script which downloads all photos from your Flickr library.

1. First, you need to get your Flickr-API keys. You can do this on the [page](https://www.flickr.com/services/apps/create/noncommercial/)

2. Save these secrets to `api_secrets.json`:
```shell
cat > api_secrets.json
{
    "api_key": "<hash>",
    "api_secret": "<hash>"
}
```

3. Create virtual env and run the script:
```shell
python3 -m venv .venv && source .venv/bin/activate && pip install -r req.txt
./dump.py --help
./dump.py
```