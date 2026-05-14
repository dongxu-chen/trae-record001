import argparse
import smtplib
import threading
import time
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from convert import EbookConverter
from format_detector import FormatDetector


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    sender: str
    password: str
    recipients: list[str] = field(default_factory=list)
    use_ssl: bool = True


class FolderWatcher:
    def __init__(
        self,
        watch_dir: str,
        output_format: str,
        output_dir: Optional[str] = None,
        poll_interval: int = 5,
        calibre_path: Optional[str] = None,
        email_config: Optional[EmailConfig] = None,
        optimize_images: bool = False,
        generate_toc: bool = False,
        max_workers: int = 4
    ):
        self.watch_dir = Path(watch_dir)
        self.output_format = output_format
        self.output_dir = Path(output_dir) if output_dir else None
        self.poll_interval = poll_interval
        self.calibre_path = calibre_path
        self.email_config = email_config
        self.optimize_images = optimize_images
        self.generate_toc = generate_toc
        self.max_workers = max_workers
        self._stop_event = threading.Event()
        self._known_files: set[str] = set()
        self._lock = threading.Lock()

    def _scan_initial(self) -> None:
        with self._lock:
            self._known_files.clear()
            if self.watch_dir.exists():
                for item in self.watch_dir.rglob('*'):
                    if item.is_file():
                        self._known_files.add(str(item.resolve()))

    def _get_new_files(self) -> list[str]:
        new_files: list[str] = []
        with self._lock:
            if not self.watch_dir.exists():
                return new_files
            for item in self.watch_dir.rglob('*'):
                if item.is_file():
                    resolved = str(item.resolve())
                    if resolved not in self._known_files:
                        if FormatDetector.is_supported(resolved):
                            new_files.append(resolved)
                        self._known_files.add(resolved)
        return new_files

    def _send_email(self, subject: str, body: str) -> bool:
        if self.email_config is None or not self.email_config.recipients:
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config.sender
            msg['To'] = ', '.join(self.email_config.recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if self.email_config.use_ssl:
                server = smtplib.SMTP_SSL(self.email_config.smtp_host, self.email_config.smtp_port)
            else:
                server = smtplib.SMTP(self.email_config.smtp_host, self.email_config.smtp_port)
                server.starttls()

            server.login(self.email_config.sender, self.email_config.password)
            server.sendmail(self.email_config.sender, self.email_config.recipients, msg.as_string())
            server.quit()
            return True
        except Exception:
            return False

    def _process_files(self, files: list[str]) -> tuple[int, int]:
        if not files:
            return 0, 0

        converter = EbookConverter(
            output_format=self.output_format,
            output_dir=str(self.output_dir) if self.output_dir else None,
            calibre_path=self.calibre_path,
            max_workers=self.max_workers
        )

        results = converter.batch_convert(files)
        success = sum(1 for r in results if r.success)
        failed = len(results) - success
        return success, failed

    def start(self) -> None:
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self._scan_initial()

        print(f'Watching: {self.watch_dir}')
        print(f'Output format: {self.output_format}')
        if self.output_dir:
            print(f'Output dir: {self.output_dir}')

        while not self._stop_event.is_set():
            new_files = self._get_new_files()
            if new_files:
                print(f'\nDetected {len(new_files)} new file(s)...')
                success, failed = self._process_files(new_files)

                subject = f'Ebook Conversion: {success} success, {failed} failed'
                body = f'Files: {len(new_files)} processed\nSuccess: {success}\nFailed: {failed}\n\nWatched: {self.watch_dir}'
                self._send_email(subject, body)

                if failed > 0:
                    print(f'Conversion: {success} success, {failed} failed (email sent)')
                else:
                    print(f'Conversion: {success} success')

            self._stop_event.wait(self.poll_interval)

    def stop(self) -> None:
        self._stop_event.set()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Watch folder and auto-convert ebooks'
    )
    parser.add_argument('watch_dir', help='Directory to watch')
    parser.add_argument('-f', '--format', required=True, help='Output format')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-i', '--interval', type=int, default=5, help='Poll interval in seconds')
    parser.add_argument('--calibre-path', help='Calibre install path')
    parser.add_argument('--optimize-images', action='store_true', help='Optimize images in EPUB')
    parser.add_argument('--generate-toc', action='store_true', help='Auto-generate TOC from headings')
    parser.add_argument('-w', '--workers', type=int, default=4, help='Max workers')
    parser.add_argument('--smtp-host', help='SMTP server host')
    parser.add_argument('--smtp-port', type=int, default=465, help='SMTP port (default 465)')
    parser.add_argument('--smtp-user', help='SMTP sender email')
    parser.add_argument('--smtp-pass', help='SMTP password')
    parser.add_argument('--smtp-recipient', action='append', default=[], help='Recipient email (repeatable)')
    parser.add_argument('--smtp-no-ssl', action='store_true', help='Use STARTTLS instead of SSL')

    args = parser.parse_args()

    email_config = None
    if args.smtp_host and args.smtp_user and args.smtp_pass:
        email_config = EmailConfig(
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            sender=args.smtp_user,
            password=args.smtp_pass,
            recipients=args.smtp_recipient or [args.smtp_user],
            use_ssl=not args.smtp_no_ssl
        )

    watcher = FolderWatcher(
        watch_dir=args.watch_dir,
        output_format=args.format,
        output_dir=args.output,
        poll_interval=args.interval,
        calibre_path=args.calibre_path,
        email_config=email_config,
        optimize_images=args.optimize_images,
        generate_toc=args.generate_toc,
        max_workers=args.workers
    )

    try:
        watcher.start()
    except KeyboardInterrupt:
        print('\nStopped by user')
        watcher.stop()


if __name__ == '__main__':
    main()
