"""Transfer-layer package."""

from ftp_client.transfer.downloader import Downloader


def create_downloader(ftp_client: object, logger: object | None = None) -> Downloader:
    """Create a downloader wired to an FTP protocol client."""
    return Downloader(
        ftp_client.connection,
        logger=logger,
        list_dir=ftp_client.list_dir,
        cwd=getattr(ftp_client, "cwd", None),
    )


__all__ = ["Downloader", "create_downloader"]
