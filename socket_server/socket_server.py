import os
import socket
from datetime import datetime


class SocketServer:
    def __init__(self):
        self.bufsize = 1024  # 버퍼 크기 설정
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read()  # 응답 파일 읽기

        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        """디렉토리 생성"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def recv_request(self, clnt_sock):
        """헤더 + Content-Length 만큼의 본문까지 전부 수신"""
        data = b""
        # 1) 헤더 끝(\r\n\r\n)까지 수신
        while b"\r\n\r\n" not in data:
            chunk = clnt_sock.recv(self.bufsize)
            if not chunk:
                return data
            data += chunk

        header_end = data.index(b"\r\n\r\n") + 4
        header_text = data[:header_end].decode("utf-8", errors="replace")

        # 2) curl이 Expect: 100-continue를 보내면 먼저 응답해 줘야 본문을 보냄
        if "expect: 100-continue" in header_text.lower():
            clnt_sock.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")

        # 3) Content-Length 만큼 본문 수신
        content_length = 0
        for line in header_text.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())

        while len(data) - header_end < content_length:
            chunk = clnt_sock.recv(self.bufsize)
            if not chunk:
                break
            data += chunk
        return data

    def save_request(self, data, timestamp):
        """실습 1: 요청 원문을 request/년-월-일-시-분-초.bin 으로 저장"""
        path = os.path.join(self.DIR_PATH, timestamp + ".bin")
        with open(path, "wb") as f:
            f.write(data)
        print(f"Saved request: {path}")

    def save_multipart_image(self, data, timestamp):
        """실습 2: multipart 본문에서 이미지 파트만 잘라 파일로 저장"""
        header_end = data.index(b"\r\n\r\n") + 4
        header_text = data[:header_end].decode("utf-8", errors="replace")
        body = data[header_end:]

        # boundary 추출
        boundary = None
        for line in header_text.split("\r\n"):
            if line.lower().startswith("content-type:") and "boundary=" in line:
                boundary = line.split("boundary=", 1)[1].strip().strip('"')
        if boundary is None:
            print("Not multipart. Skip image saving.")
            return

        delimiter = b"--" + boundary.encode()
        for part in body.split(delimiter):
            if b"\r\n\r\n" not in part:
                continue
            part_header, part_body = part.split(b"\r\n\r\n", 1)
            part_header_text = part_header.decode("utf-8", errors="replace")

            if "filename=" in part_header_text:  # 파일 파트(이미지)
                # 파트 끝의 \r\n 제거 (다음 boundary 앞의 줄바꿈)
                if part_body.endswith(b"\r\n"):
                    part_body = part_body[:-2]

                filename = part_header_text.split("filename=", 1)[1].split("\r\n")[0]
                filename = filename.split(";")[0].strip().strip('"')
                ext = os.path.splitext(filename)[1] or ".jpg"

                path = os.path.join(self.DIR_PATH, timestamp + ext)
                with open(path, "wb") as f:
                    f.write(part_body)
                print(f"Saved image: {path} ({len(part_body)} bytes)")
            else:  # 텍스트 필드 (title, text 등)
                print("Field:", part_header_text.strip().replace("\r\n", " | "),
                      "=>", part_body.strip()[:50])

    def run(self, ip, port):
        """서버 실행"""
        # 소켓 생성
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)
        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")

        try:
            while True:
                # 클라이언트의 요청 대기
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0)  # 타임아웃 설정 (5초)
                print("Request message...\r\n")

                try:
                    response = self.recv_request(clnt_sock)
                    if response:
                        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                        self.save_request(response, timestamp)       # 실습 1
                        self.save_multipart_image(response, timestamp)  # 실습 2
                except socket.timeout:
                    print("Timeout while receiving request.")

                # 응답 전송
                clnt_sock.sendall(self.RESPONSE)

                # 클라이언트 소켓 닫기
                clnt_sock.close()
        except KeyboardInterrupt:
            print("\r\nStop the server...")

        # 서버 소켓 닫기
        self.sock.close()


if __name__ == "__main__":
    server = SocketServer()
    server.run("127.0.0.1", 8000)