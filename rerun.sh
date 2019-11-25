result=1
while [ $result -ne 0 ]; do
    python3 scraper.py
    result=$?
done