#!/usr/bin/env python3
"""
UTF-8 Mojibake Repair Tool

This script safely repairs files that have been corrupted by being read with the wrong
character encoding and then saved as UTF-8. It uses multiple detection strategies
to ensure that only genuinely corrupted files are processed.
"""

import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RepairResult(Enum):
    """Possible outcomes of a repair attempt."""
    SUCCESS = "success"
    SKIPPED_CLEAN = "skipped_clean"
    SKIPPED_BINARY = "skipped_binary"
    SKIPPED_NO_MOJIBAKE = "skipped_no_mojibake"
    FAILED_READ_ERROR = "failed_read_error"
    FAILED_WRITE_ERROR = "failed_write_error"
    FAILED_MAX_ITERATIONS = "failed_max_iterations"


@dataclass
class RepairConfig:
    """Configuration parameters for mojibake repair."""
    max_iterations: int = 5
    ascii_threshold: float = 0.8
    japanese_threshold: float = 0.1
    suspicious_pattern_threshold: int = 2
    binary_check_bytes: int = 1024

    # File extensions to skip (binary files)
    skip_extensions: Tuple[str, ...] = (
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
        '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
        '.exe', '.dll', '.so', '.dylib'
    )

    # Encoding strategies to try for repair
    repair_strategies: Tuple[str, ...] = (
        'latin-1', 'mac_roman', 'cp1252', 'shift_jis', 'euc_jp'
    )


class MojibakeDetector:
    """Detects mojibake patterns in UTF-8 text."""

    # Common mojibake patterns (double-encoded UTF-8)
    MOJIBAKE_PATTERNS = [
        r'[ãâ][â¢â£â¤â¥â¦â§â¨â©âªâ«â¬â­â®â¯]',  # Common UTF-8 as latin-1 patterns
        r'ã{3,}',  # Multiple consecutive ã characters
        r'â.{1,3}â',  # Suspicious sequences with â
    ]

    # Specific suspicious character combinations
    SUSPICIOUS_SEQUENCES = [
        'ã',  # Very common in mojibake
        'â',  # Another common pattern
        'Ã',  # Capital patterns
        'Â',  # Control char patterns
'ç', 'æ', 'é', 'è'  # Other common corruptions
    ]

# Unicode ranges for legitimate characters
    JAPANESE_RANGES = [
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0x4E00, 0x9FAF),  # CJK Unified Ideographs
        (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
    ]

    def __init__(self, config: RepairConfig):
        self.config = config

    def has_mojibake_patterns(self, text: str) -> bool:
        """Check if text contains typical mojibake patterns."""
        # Check regex patterns
        for pattern in self.MOJIBAKE_PATTERNS:
            if re.search(pattern, text):
                return True

        # Count suspicious character sequences
        suspicious_count = sum(
            text.count(seq) for seq in self.SUSPICIOUS_SEQUENCES
        )

        return suspicious_count > self.config.suspicious_pattern_threshold

    def appears_clean_utf8(self, text: str) -> bool:
        """Check if text appears to be clean, readable UTF-8."""
        if not text:
            return True

        # First check for mojibake patterns - if found, not clean
        if self.has_mojibake_patterns(text):
            return False

        # High ASCII ratio indicates likely clean text
        ascii_count = sum(1 for c in text if ord(c) < 128)
        ascii_ratio = ascii_count / len(text)

        if ascii_ratio > self.config.ascii_threshold:
            return True

        # Check for legitimate Japanese/Unicode characters
        japanese_count = sum(
            1 for char in text
            if any(start <= ord(char) <= end for start, end in self.JAPANESE_RANGES)
        )

        japanese_ratio = japanese_count / len(text)
        return japanese_ratio > self.config.japanese_threshold

    def should_repair(self, text: str) -> bool:
        """Determine if text should be repaired based on detection criteria."""
        return (
            not self.appears_clean_utf8(text) and
            self.has_mojibake_patterns(text)
        )


class FileProcessor:
    """Handles file I/O operations for mojibake repair."""

    def __init__(self, config: RepairConfig):
        self.config = config

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on extension."""
        return file_path.suffix.lower() in self.config.skip_extensions

    def is_binary_file(self, content: bytes) -> bool:
        """Check if file appears to be binary based on null bytes."""
        check_size = min(len(content), self.config.binary_check_bytes)
        return b'\x00' in content[:check_size]

    def read_file_safely(self, file_path: Path) -> Optional[str]:
        """Read file content as UTF-8, return None if not possible."""
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read()

            if self.is_binary_file(raw_content):
                return None

            return raw_content.decode('utf-8')

        except (IOError, UnicodeDecodeError):
            return None

    def write_file_safely(self, file_path: Path, content: str) -> bool:
        """Write content to file as UTF-8, return success status."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except IOError:
            return False


class MojibakeRepairer:
    """Core logic for repairing mojibake corruption."""

    def __init__(self, config: RepairConfig):
        self.config = config
        self.detector = MojibakeDetector(config)
        self.file_processor = FileProcessor(config)

    def try_repair_with_strategy(self, text: str, strategy: str) -> Optional[str]:
        """Attempt to repair text using a specific encoding strategy."""
        try:
            # Reverse the corruption by encoding with the assumed wrong encoding
            repaired_bytes = text.encode(strategy)

            # Decode back as UTF-8
            repaired_text = repaired_bytes.decode('utf-8')

            print(f"  Trying {strategy}: '{text[:20]}...' -> '{repaired_text[:20]}...'")

            # Validate the repair
            if (not self.detector.has_mojibake_patterns(repaired_text) and
                self.detector.appears_clean_utf8(repaired_text)):
                print(f"  ✓ Strategy {strategy} successful!")
                return repaired_text
            else:
                print(f"  ✗ Strategy {strategy} failed validation")

        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            print(f"  ✗ Strategy {strategy} failed: {e}")

        return None

    def repair_text(self, text: str) -> Optional[str]:
        """Attempt to repair mojibake in text using all available strategies."""
        original_bytes = text.encode('utf-8')

        for strategy in self.config.repair_strategies:
            repaired_text = self.try_repair_with_strategy(text, strategy)

            if repaired_text is not None:
                # Ensure we actually changed something
                if repaired_text.encode('utf-8') != original_bytes:
                    return repaired_text

        return None

    def repair_file(self, file_path: Path) -> RepairResult:
        """Repair a single file, returning the result status."""
        # Skip based on file extension
        if self.file_processor.should_skip_file(file_path):
            return RepairResult.SKIPPED_BINARY

        # Read file content
        original_text = self.file_processor.read_file_safely(file_path)
        if original_text is None:
            return RepairResult.FAILED_READ_ERROR

        # Check if file needs repair
        if not self.detector.should_repair(original_text):
            return RepairResult.SKIPPED_NO_MOJIBAKE

        # Attempt iterative repair
        current_text = original_text
        iterations = 0

        print(f"Detected potential mojibake in {file_path}, attempting repair...")

        while iterations < self.config.max_iterations:
            iterations += 1

            repaired_text = self.repair_text(current_text)
            if repaired_text is None:
                break

            # Write repaired content
            if not self.file_processor.write_file_safely(file_path, repaired_text):
                return RepairResult.FAILED_WRITE_ERROR

            print(f"Successfully repaired {file_path} in iteration {iterations}")

            # Check if further repair is needed
            if not self.detector.should_repair(repaired_text):
                return RepairResult.SUCCESS

            current_text = repaired_text

        if iterations == self.config.max_iterations:
            print(f"Warning: Max iterations reached for {file_path}", file=sys.stderr)
            return RepairResult.FAILED_MAX_ITERATIONS

        return RepairResult.SKIPPED_NO_MOJIBAKE


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        sys.exit(0)

    config = RepairConfig()
    repairer = MojibakeRepairer(config)

    for file_path_str in sys.argv[1:]:
        file_path = Path(file_path_str)
        result = repairer.repair_file(file_path)

        # Log result for debugging (only errors and successes)
        if result == RepairResult.FAILED_READ_ERROR:
            print(f"Error: Could not read {file_path}", file=sys.stderr)
        elif result == RepairResult.FAILED_WRITE_ERROR:
            print(f"Error: Could not write to {file_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

