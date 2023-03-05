from flask import Flask
from flask import jsonify
from flask import request

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

baseURL = "https://opensource.samsung.com"
searchURL = baseURL + "/uploadSearch?searchValue="
modalURL = baseURL + "/downSrcMPop?uploadId="
downSrcURL = baseURL + "/downSrcCode"

@app.route("/")
def home():
    return jsonify({
        "msg": "Hello, World!"
    })

@app.route("/search")
def search():
    query = request.args.get("query")

    req = requests.get(searchURL + quote_plus(query))
    parse = BeautifulSoup(req.text, "html.parser")
    searchTable = parse.find("table", class_="tbl-downList")

    rowSearchTable = searchTable.find_all("tr", class_="")
    dataList = []
    for row in rowSearchTable:
        dataSearchTable = row.find_all("td")

        sourceModel = dataSearchTable[1].text.strip()
        sourceVersion = dataSearchTable[2].text.strip()
        sourceDesc = dataSearchTable[3].text.strip()
        sourceUploadId = dataSearchTable[5].find("a")["href"].split("'")[1]

        dataList.append({
            "upload_id": sourceUploadId,
            "source_model": sourceModel,
            "source_version": sourceVersion,
            "source_description": sourceDesc,
        })

    return jsonify(dataList)

@app.route("/download")
def download():
    uploadId = request.args.get("uploadId")

    req = requests.get(modalURL + uploadId)
    parse = BeautifulSoup(req.text, "html.parser")

    # Download the source
    requestData = {
        "uploadId": uploadId,
        "attachIds": parse.find_all("input", type="checkbox")[1]["id"],
        "_csrf": parse.find_all(attrs={"name": "_csrf"})[0]["value"],
        "token": parse.find_all(id="token")[0]["value"].encode("utf-8"),
        "downloadPurpose": "AOP",
    }

    requestHeader = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55",
    }

    requestCookie = {"JSESSIONID": req.cookies.get("JSESSIONID")}

    requestDown = requests.post(downSrcURL, data=requestData, headers=requestHeader, cookies=requestCookie, stream=True)

    sourceType = requestDown.headers["Content-Type"]
    sourceDisposition = requestDown.headers["Content-Disposition"]
    sourceSize = int(requestDown.headers["Content-Length"])

    return requestDown.iter_content(chunk_size=128*1024), {"Content-Type": sourceType, "Content-Disposition": sourceDisposition, "Content-Length": sourceSize}

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
