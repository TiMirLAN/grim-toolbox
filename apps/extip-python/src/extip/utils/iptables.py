from hashlib import sha256
from subprocess import check_output


def build_routes_hash() -> str:
    output = check_output("ip route show", shell=True, text=True)
    return sha256(output.encode()).hexdigest()


class IptablesService:
    def __init__(self) -> None:
        self.table_cache: str = build_routes_hash()

    def check_table_changed(self) -> bool:
        cache = build_routes_hash()
        if cache == self.table_cache:
            return False
        self.table_cache = cache
        return True
