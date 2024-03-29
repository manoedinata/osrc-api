from flask import Flask
from flask import jsonify
from flask import request

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    req = requests.get(searchURL + quote_plus(query), verify=False)
    parse = BeautifulSoup(req.text, "html.parser")

    if parse.find(class_="no-results"):
        return jsonify({
            "msg": "No sources found"
        }), 404

    # Pagination
    listOfReq = []
    listOfReq.append(req) # Append first request

    pagination = parse.find(class_="paginate")
    if len(pagination.find_all("a")) > 1:
        for num in pagination.find_all("a")[1:-1]:
            num = num.text.strip()
            req = requests.get(searchURL + quote_plus(query) + "&page=" + num, verify=False)
            listOfReq.append(req)

    dataList = []
    for req in listOfReq:
        parse = BeautifulSoup(req.text, "html.parser")
        searchTable = parse.find("table", class_="tbl-downList")

        rowSearchTable = searchTable.find_all("tr", class_="")
        for row in rowSearchTable:
            dataSearchTable = row.find_all("td")

            sourceModel = dataSearchTable[1].text.strip()
            sourceUploadId = dataSearchTable[5].find("a")["href"].split("'")[1]
            sourceVersion = dataSearchTable[2].encode_contents().decode().strip()
            if "<br/>" in sourceVersion:
                sourceVersion = [x for x in sourceVersion.split("<br/>")]
            sourceDesc = dataSearchTable[3].encode_contents().decode().strip()
            if "<br/>" in sourceDesc:
                sourceDesc = [x for x in sourceDesc.split("<br/>")]

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
    sourceNum = request.args.get("sourceNum")
    if not sourceNum:
        sourceNum = 1

    req = requests.get(modalURL + uploadId, verify=False)
    parse = BeautifulSoup(req.text, "html.parser")

    # Download the source
    requestData = {
        "uploadId": uploadId,
        "attachIds": parse.find_all("input", type="checkbox")[int(sourceNum)]["id"],
        "_csrf": parse.find_all(attrs={"name": "_csrf"})[0]["value"],
        "token": parse.find_all(id="token")[0]["value"].encode("utf-8"),
        "downloadPurpose": "AOP",
    }

    requestHeader = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55",
    }

    requestCookie = {"JSESSIONID": req.cookies.get("JSESSIONID")}

    requestDown = requests.post(downSrcURL, data=requestData, headers=requestHeader, cookies=requestCookie, verify=False, stream=True)

    sourceType = requestDown.headers["Content-Type"]
    sourceDisposition = requestDown.headers["Content-Disposition"]
    sourceSize = int(requestDown.headers["Content-Length"])

    return requestDown.iter_content(chunk_size=128*1024), {"Content-Type": sourceType, "Content-Disposition": sourceDisposition, "Content-Length": sourceSize}

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
