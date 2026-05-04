import asyncio
from io import BufferedIOBase
from typing import Any, Dict

import aiohttp

from ..client import MaxClient, USER_AGENT


async def download_video(
    client: MaxClient,
    chat_id: int,
    message_id: str,
    video_id: int,
) -> str:
    response = await client.invoke_method(
        opcode=83,
        payload={"videoId": video_id, "chatId": chat_id, "messageId": message_id},
    )
    formats = dict(response["payload"])
    formats.pop("cache", None)
    formats.pop("EXTERNAL", None)
    return str(next(iter(formats.values())))


async def download_file(
    client: MaxClient,
    chat_id: int,
    message_id: str,
    file_id: int,
) -> str:
    response = await client.invoke_method(
        opcode=88,
        payload={"fileId": file_id, "chatId": chat_id, "messageId": message_id},
    )
    return str(response["payload"]["url"])


async def upload_photo(
    client: MaxClient,
    chat_id: int,
    stream: BufferedIOBase,
    filename: str = "image.jpg",
) -> Dict[str, Any]:
    response = await client.invoke_method(opcode=80, payload={"count": 1})
    upload_url = response["payload"]["url"]
    upload_response = await _upload(
        client=client,
        chat_id=chat_id,
        url=upload_url,
        stream=stream,
        attach_type="PHOTO",
        filename=filename,
        mimetype="image/jpeg",
    )
    payload = await upload_response.json()
    token = next(iter(payload["photos"].values()))["token"]
    return {"_type": "PHOTO", "photoToken": token}


async def upload_video(
    client: MaxClient,
    chat_id: int,
    stream: BufferedIOBase,
    filename: str = "video.mp4",
) -> Dict[str, Any]:
    response = await client.invoke_method(opcode=82, payload={"count": 1})
    info = response["payload"]["info"][0]
    video_id = int(info["videoId"])
    token = str(info["token"])
    await _upload(
        client=client,
        chat_id=chat_id,
        url=info["url"],
        stream=stream,
        attach_type="VIDEO",
        filename=filename,
        mimetype="video/mp4",
    )
    future: asyncio.Future[Dict[str, Any]] = asyncio.get_running_loop().create_future()
    client._video_pending[video_id] = future
    await future
    return {"_type": "VIDEO", "videoId": video_id, "token": token}


async def upload_file(
    client: MaxClient,
    chat_id: int,
    stream: BufferedIOBase,
    filename: str = "file.bin",
) -> Dict[str, Any]:
    response = await client.invoke_method(opcode=87, payload={"count": 1})
    info = response["payload"]["info"][0]
    file_id = int(info["fileId"])
    await _upload(
        client=client,
        chat_id=chat_id,
        url=info["url"],
        stream=stream,
        attach_type="FILE",
        filename=filename,
        mimetype="application/octet-stream",
    )
    future: asyncio.Future[Dict[str, Any]] = asyncio.get_running_loop().create_future()
    client._file_pending[file_id] = future
    await future
    return {"_type": "FILE", "fileId": file_id}


async def _upload(
    client: MaxClient,
    chat_id: int,
    url: str,
    stream: BufferedIOBase,
    attach_type: str,
    filename: str,
    mimetype: str,
) -> aiohttp.ClientResponse:
    await client.invoke_method(opcode=65, payload={"chatId": chat_id, "type": attach_type})
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Origin": "https://web.max.ru",
        "Referer": "https://web.max.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": USER_AGENT,
    }
    if client._http_pool is None:
        client._http_pool = aiohttp.ClientSession()
    data = aiohttp.FormData()
    data.add_field("file", stream, filename=filename, content_type=mimetype)
    response = await client._http_pool.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response
