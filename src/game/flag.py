"""플래그 관리 시스템"""

from typing import Set, Dict


class FlagManager:
    """플래그를 관리하는 클래스"""
    
    def __init__(self):
        self.flags: Set[str] = set()
        self.persistent_flags: Set[str] = set()
    
    def set_flag(self, flag_id: str, persistent: bool = False):
        """플래그 설정"""
        self.flags.add(flag_id)
        if persistent:
            self.persistent_flags.add(flag_id)
    
    def unset_flag(self, flag_id: str):
        """플래그 해제"""
        self.flags.discard(flag_id)
        self.persistent_flags.discard(flag_id)
    
    def has_flag(self, flag_id: str) -> bool:
        """플래그 확인"""
        return flag_id in self.flags
    
    def has_all_flags(self, flag_ids: list) -> bool:
        """모든 플래그 확인"""
        return all(self.has_flag(flag_id) for flag_id in flag_ids)
    
    def has_any_flag(self, flag_ids: list) -> bool:
        """하나라도 플래그 확인"""
        return any(self.has_flag(flag_id) for flag_id in flag_ids)
    
    def apply_flag_changes(self, changes: list):
        """플래그 변경 일괄 적용"""
        for change in changes:
            flag_id = change.get("flag", "")
            action = change.get("action", "set")  # 'set', 'unset', 'toggle'
            
            if action == "set":
                self.set_flag(flag_id, change.get("persistent", False))
            elif action == "unset":
                self.unset_flag(flag_id)
            elif action == "toggle":
                if self.has_flag(flag_id):
                    self.unset_flag(flag_id)
                else:
                    self.set_flag(flag_id, change.get("persistent", False))
    
    def get_all_flags(self) -> Set[str]:
        """모든 플래그 반환"""
        return self.flags.copy()
