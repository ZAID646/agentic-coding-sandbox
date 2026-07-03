import io
import os
import base64
import re
import docker
from src.models import SandboxResult
from src.config import SANDBOX_IMAGE, SANDBOX_TIMEOUT


DOCKER_SOCKET = "unix:///Users/zaid/.colima/default/docker.sock"

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
_client: docker.DockerClient | None = None


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.DockerClient(base_url=DOCKER_SOCKET)
    return _client


def _wrap_script(script: str) -> str:
    b64_script = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return (
        "import base64, os\n"
        f"exec(base64.b64decode('{b64_script}').decode())\n"
        "for f in os.listdir('/tmp'):\n"
        "    ext = os.path.splitext(f)[1].lower()\n"
        f"    if ext in {list(_IMAGE_EXTENSIONS)}:\n"
        "        with open(os.path.join('/tmp', f), 'rb') as imgf:\n"
        "            b = base64.b64encode(imgf.read()).decode()\n"
        "            print(f'__SANDBOX_FILE__{f}__{b}__SANDBOX_ENDFILE__')\n"
    )


def execute_code(script: str, requirements: list[str] | None = None) -> SandboxResult:
    client = _get_client()
    container = None
    try:
        if requirements:
            req_lines = "\n".join(
                f"RUN pip install --quiet --no-cache-dir {pkg}"
                for pkg in requirements
            )
            dockerfile = f"FROM {SANDBOX_IMAGE}\n{req_lines}\n"
            img, _ = client.images.build(
                fileobj=io.BytesIO(dockerfile.encode("utf-8")), rm=True
            )
            image = img.id
        else:
            image = SANDBOX_IMAGE

        wrapped = _wrap_script(script)

        container = client.containers.create(
            image=image,
            command=["python3", "-c", wrapped],
            detach=True,
            network_disabled=False,
            read_only=True,
            tmpfs={"/tmp": "size=64m"},
            environment={"MPLCONFIGDIR": "/tmp"},
            mem_limit="512m",
            pids_limit=64,
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
        )

        container.start()
        result = container.wait(timeout=SANDBOX_TIMEOUT)
        raw_logs = container.logs(stdout=True, stderr=True, tail=10000)

        stdout, stderr = _demux_logs(raw_logs)
        clean_stdout, files = _parse_file_blocks(stdout)

        return SandboxResult(
            stdout=clean_stdout or "",
            stderr=stderr or "",
            exit_code=result.get("StatusCode", -1),
            success=result.get("StatusCode", 1) == 0,
            files=files,
        )
    except docker.errors.APIError as e:
        return SandboxResult(
            stdout="", stderr=str(e), exit_code=-1, success=False
        )
    except Exception as e:
        return SandboxResult(
            stdout="", stderr=str(e), exit_code=-1, success=False
        )
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass


def _parse_file_blocks(text: str) -> tuple[str, dict[str, str]]:
    files = {}
    pattern = r"__SANDBOX_FILE__(.+?)__(.{10,}?)__SANDBOX_ENDFILE__"

    def replace_block(m):
        name = m.group(1)
        b64 = m.group(2)
        files[name] = b64
        return ""

    clean = re.sub(pattern, replace_block, text, flags=re.DOTALL)
    return clean.strip(), files


def _demux_logs(raw: bytes) -> tuple[str, str]:
    if not raw:
        return "", ""

    stdout_parts = []
    stderr_parts = []
    i = 0
    while i < len(raw):
        if i + 8 > len(raw):
            stdout_parts.append(raw[i:].decode("utf-8", errors="replace"))
            break
        stream_type = raw[i]
        _ = int.from_bytes(raw[i + 4 : i + 8], "big")
        i += 8
        chunk_size = int.from_bytes(raw[i - 4 : i], "big")
        if i + chunk_size > len(raw):
            chunk = raw[i:]
        else:
            chunk = raw[i : i + chunk_size]
        i += chunk_size
        decoded = chunk.decode("utf-8", errors="replace")
        if stream_type == 1:
            stdout_parts.append(decoded)
        elif stream_type == 2:
            stderr_parts.append(decoded)
        else:
            stdout_parts.append(decoded)

    return "".join(stdout_parts), "".join(stderr_parts)
