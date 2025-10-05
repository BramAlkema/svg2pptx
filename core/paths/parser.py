#!/usr/bin/env python3
"""
SVG Path Data Parser

This module implements a clean path parser that focuses solely on parsing SVG
path data into structured commands without performing any coordinate transformations.

Key Features:
- Parses all SVG path commands (M, L, H, V, C, S, Q, T, A, Z)
- Handles relative vs absolute commands correctly
- Robust error handling for malformed path data
- No coordinate transformations (handled by CoordinateSystem)
- Clean separation of concerns
"""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .interfaces import PathParser as PathParserInterface
from .architecture import (
    PathCommand, PathCommandType, PathParseError
)

logger = logging.getLogger(__name__)


@dataclass
class ParsedToken:
    """Represents a parsed token from SVG path data."""
    token_type: str  # 'command' or 'number'
    value: str
    position: int


class PathParser(PathParserInterface):
    """
    Clean SVG path parser implementation.

    This parser focuses on extracting structured path commands from SVG path
    data strings without performing any coordinate transformations. All coordinate
    values are preserved in their original SVG format.
    """

    # Mapping of SVG command letters to PathCommandType
    COMMAND_MAPPING = {
        'M': PathCommandType.MOVE_TO,     'm': PathCommandType.MOVE_TO,
        'L': PathCommandType.LINE_TO,     'l': PathCommandType.LINE_TO,
        'H': PathCommandType.HORIZONTAL,  'h': PathCommandType.HORIZONTAL,
        'V': PathCommandType.VERTICAL,    'v': PathCommandType.VERTICAL,
        'C': PathCommandType.CUBIC_CURVE, 'c': PathCommandType.CUBIC_CURVE,
        'S': PathCommandType.SMOOTH_CUBIC,'s': PathCommandType.SMOOTH_CUBIC,
        'Q': PathCommandType.QUADRATIC,   'q': PathCommandType.QUADRATIC,
        'T': PathCommandType.SMOOTH_QUAD, 't': PathCommandType.SMOOTH_QUAD,
        'A': PathCommandType.ARC,         'a': PathCommandType.ARC,
        'Z': PathCommandType.CLOSE_PATH,  'z': PathCommandType.CLOSE_PATH,
    }

    # Expected parameter counts for each command type
    PARAMETER_COUNTS = {
        PathCommandType.MOVE_TO: 2,      # x, y
        PathCommandType.LINE_TO: 2,      # x, y
        PathCommandType.HORIZONTAL: 1,   # x
        PathCommandType.VERTICAL: 1,     # y
        PathCommandType.CUBIC_CURVE: 6,  # x1, y1, x2, y2, x, y
        PathCommandType.SMOOTH_CUBIC: 4, # x2, y2, x, y
        PathCommandType.QUADRATIC: 4,    # x1, y1, x, y
        PathCommandType.SMOOTH_QUAD: 2,  # x, y
        PathCommandType.ARC: 7,          # rx, ry, x-axis-rotation, large-arc-flag, sweep-flag, x, y
        PathCommandType.CLOSE_PATH: 0,   # no parameters
    }

    def __init__(self, enable_logging: bool = True):
        """Initialize path parser with regex compilation."""
        super().__init__(enable_logging)

        # Compile regex patterns for efficient parsing
        self._number_pattern = re.compile(
            r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
        )
        self._command_pattern = re.compile(r'[MmLlHhVvCcSsQqTtAaZz]')

        # Combined pattern for tokenization
        self._token_pattern = re.compile(
            r'([MmLlHhVvCcSsQqTtAaZz])|'  # Commands
            r'([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)'  # Numbers
        )

        self.log_debug("PathParser initialized with compiled regex patterns")

    def parse_path_data(self, path_data: str) -> List[PathCommand]:
        """
        Parse SVG path data string into structured path commands.

        Args:
            path_data: SVG path 'd' attribute string (e.g., "M10,20 L30,40 Z")

        Returns:
            List of PathCommand objects with original SVG coordinates

        Raises:
            PathParseError: If path data is malformed or invalid
        """
        try:
            if not path_data or not path_data.strip():
                return []

            # Clean and normalize the path data
            normalized_data = self._normalize_path_data(path_data)

            # Tokenize the path data
            tokens = self._tokenize_path_data(normalized_data)

            # Parse tokens into commands
            commands = self._parse_tokens(tokens)

            # Validate the parsed commands
            self._validate_commands(commands)

            self.log_debug(f"Successfully parsed {len(commands)} path commands")
            return commands

        except Exception as e:
            raise PathParseError(f"Failed to parse path data '{path_data[:50]}...': {e}")

    def validate_path_data(self, path_data: str) -> bool:
        """
        Validate SVG path data syntax without full parsing.

        Args:
            path_data: SVG path 'd' attribute string

        Returns:
            True if path data has valid syntax, False otherwise
        """
        try:
            if not path_data or not path_data.strip():
                return True  # Empty path is valid

            # Try to parse - if it fails, it's invalid
            commands = self.parse_path_data(path_data)
            return len(commands) > 0

        except Exception:
            return False

    def _normalize_path_data(self, path_data: str) -> str:
        """
        Normalize path data for easier parsing.

        Args:
            path_data: Raw SVG path data

        Returns:
            Normalized path data string
        """
        # Remove extra whitespace and normalize separators
        normalized = re.sub(r'\s+', ' ', path_data.strip())

        # Ensure commands are separated from numbers
        normalized = re.sub(r'([MmLlHhVvCcSsQqTtAaZz])', r' \1 ', normalized)

        # Handle comma separators
        normalized = re.sub(r',', ' ', normalized)

        # Clean up multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def _tokenize_path_data(self, path_data: str) -> List[ParsedToken]:
        """
        Tokenize normalized path data into commands and numbers.

        Args:
            path_data: Normalized path data string

        Returns:
            List of ParsedToken objects
        """
        tokens = []
        position = 0

        for match in self._token_pattern.finditer(path_data):
            command, number = match.groups()

            if command:
                tokens.append(ParsedToken('command', command, position))
            elif number:
                tokens.append(ParsedToken('number', number, position))

            position += 1

        return tokens

    def _parse_tokens(self, tokens: List[ParsedToken]) -> List[PathCommand]:
        """
        Parse tokens into PathCommand objects.

        Args:
            tokens: List of parsed tokens

        Returns:
            List of PathCommand objects
        """
        commands = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token.token_type != 'command':
                raise PathParseError(f"Expected command at position {token.position}, got {token.value}")

            command_letter = token.value
            command_type = self.COMMAND_MAPPING.get(command_letter)

            if command_type is None:
                raise PathParseError(f"Unknown command '{command_letter}' at position {token.position}")

            is_relative = command_letter.islower()
            expected_params = self.PARAMETER_COUNTS[command_type]

            # Extract parameters for this command
            parameters = []
            i += 1  # Move past command

            for _ in range(expected_params):
                if i >= len(tokens) or tokens[i].token_type != 'number':
                    raise PathParseError(
                        f"Command '{command_letter}' requires {expected_params} parameters, "
                        f"but only {len(parameters)} were found"
                    )

                try:
                    param_value = float(tokens[i].value)
                    parameters.append(param_value)
                except ValueError as e:
                    raise PathParseError(f"Invalid numeric parameter '{tokens[i].value}': {e}")

                i += 1

            # Create PathCommand
            path_command = PathCommand(
                command_type=command_type,
                is_relative=is_relative,
                parameters=parameters,
                original_command=command_letter
            )

            commands.append(path_command)

            # Handle implicit commands (e.g., M followed by implicit L commands)
            implicit_commands, i = self._handle_implicit_commands(path_command, tokens, i)
            commands.extend(implicit_commands)

        return commands

    def _handle_implicit_commands(self, base_command: PathCommand, tokens: List[ParsedToken],
                                 start_index: int) -> Tuple[List[PathCommand], int]:
        """
        Handle implicit commands that follow certain base commands.

        For example, 'M 10 20 30 40' becomes 'M 10 20 L 30 40'

        Args:
            base_command: The base command that was just parsed
            tokens: All tokens
            start_index: Current position in tokens

        Returns:
            Tuple of (implicit_commands, new_index)
        """
        implicit_commands = []

        # Only MOVE_TO commands generate implicit LINE_TO commands
        if base_command.command_type != PathCommandType.MOVE_TO:
            return implicit_commands, start_index

        # Check for additional coordinate pairs after MOVE_TO
        i = start_index
        line_command_type = PathCommandType.LINE_TO
        expected_params = self.PARAMETER_COUNTS[line_command_type]

        while i + expected_params <= len(tokens):
            # Check if we have enough number tokens for a LINE_TO
            if all(i + j < len(tokens) and tokens[i + j].token_type == 'number' for j in range(expected_params)):
                # Extract parameters for implicit LINE_TO
                parameters = []
                for j in range(expected_params):
                    try:
                        param_value = float(tokens[i + j].value)
                        parameters.append(param_value)
                    except ValueError:
                        return implicit_commands, i  # Stop on invalid number

                if len(parameters) == expected_params:
                    # Create implicit LINE_TO command
                    implicit_command = PathCommand(
                        command_type=line_command_type,
                        is_relative=base_command.is_relative,  # Same relativity as MOVE_TO
                        parameters=parameters,
                        original_command='l' if base_command.is_relative else 'L'
                    )
                    implicit_commands.append(implicit_command)
                    i += expected_params
                else:
                    break
            else:
                break

        return implicit_commands, i

    def _validate_commands(self, commands: List[PathCommand]) -> None:
        """
        Validate the parsed commands for logical consistency.

        Args:
            commands: List of parsed commands to validate

        Raises:
            PathParseError: If commands are invalid
        """
        if not commands:
            return

        # First command should be MOVE_TO
        if commands[0].command_type != PathCommandType.MOVE_TO:
            raise PathParseError(
                f"Path must start with MOVE_TO command, got {commands[0].command_type}"
            )

        # Validate parameter counts
        for i, command in enumerate(commands):
            expected_count = self.PARAMETER_COUNTS[command.command_type]
            if len(command.parameters) != expected_count:
                raise PathParseError(
                    f"Command {i} ({command.original_command}) has {len(command.parameters)} "
                    f"parameters, expected {expected_count}"
                )

        self.log_debug(f"Validated {len(commands)} commands successfully")

    def get_supported_commands(self) -> List[str]:
        """Get list of supported SVG path commands."""
        return list(self.COMMAND_MAPPING.keys())

    def get_command_info(self, command_letter: str) -> Optional[Tuple[PathCommandType, int, bool]]:
        """
        Get information about a specific command.

        Args:
            command_letter: SVG command letter (e.g., 'M', 'L', 'A')

        Returns:
            Tuple of (command_type, parameter_count, is_relative) or None if unknown
        """
        command_type = self.COMMAND_MAPPING.get(command_letter)
        if command_type is None:
            return None

        parameter_count = self.PARAMETER_COUNTS[command_type]
        is_relative = command_letter.islower()

        return (command_type, parameter_count, is_relative)