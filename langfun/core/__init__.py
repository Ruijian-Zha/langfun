# Copyright 2023 The Langfun Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The core langfun module.

Symbols with name `langfun.core.*` will be seen as `langfun.*` directly.
Please see //third_party/py/langfun/__init__.py for details.
"""

# pylint: disable=g-bad-import-order
# pylint: disable=g-importing-member
# pylint: disable=g-import-not-at-top

# Interface for all langfun components.
from langfun.core.component import Component
from langfun.core.langfunc import LangFunc

# Decorator for set the positional init args for component.
from langfun.core.component import use_init_args

# Context manager for overriding the values for contextual attributes.
from langfun.core.component import context

# For backward compatibility.
as_context = context
use_context = context

# Shortcut function for overriding components attributes, usually for
# override settings.
from langfun.core.component import use_settings

from langfun.core.component import get_contextual_override

# Value marker for attribute whose values will be provided from parent
# objects or from the `pg.component_context` context manager.
from langfun.core.component import contextual

# Content subscriptions through LangFunc events and event handlers.
from langfun.core.subscription import Event
from langfun.core.subscription import EventHandler

from langfun.core.subscription import subscribe
from langfun.core.subscription import unsubscribe
from langfun.core.subscription import subscribers

from langfun.core.subscription import subscriptions
from langfun.core.subscription import clear_subscriptions

# LangFunc events.
from langfun.core.langfunc import LangFuncEvent
from langfun.core.langfunc import LangFuncRenderEvent
from langfun.core.langfunc import LangFuncCallEvent

# Helper methods for concurrent sampling.
from langfun.core.sampling import sweep
from langfun.core.sampling import random_sample

# Concurrent execute a function with parallel inputs with inheriting current
# context's defaults and overrides.
from langfun.core.concurrent import concurrent_execute
from langfun.core.concurrent import concurrent_map
from langfun.core.concurrent import with_context_access
from langfun.core.concurrent import with_retry

# Utility libraries for text formatting.
from langfun.core.text_formatting import colored
from langfun.core.text_formatting import colored_print as print  # pylint: disable=redefined-builtin
from langfun.core.text_formatting import colored_template

# Interface for natural language formattable.
from langfun.core.natural_language import NaturalLanguageFormattable

# Input/output protocols.
from langfun.core.message import Message
from langfun.core.message import UserMessage
from langfun.core.message import AIMessage
from langfun.core.message import SystemMessage
from langfun.core.message import MemoryRecord


# Message transforms.
from langfun.core.message_transform import MessageTransform


# Interfaces for languge models.
from langfun.core.language_model import LanguageModel
from langfun.core.language_model import LMSample
from langfun.core.language_model import LMSamplingOptions
from langfun.core.language_model import LMSamplingResult

# Components for building agents.
from langfun.core.memory import Memory

# Utility for console output.
from langfun.core import console

# pylint: enable=g-import-not-at-top
# pylint: enable=g-importing-member
# pylint: enable=g-bad-import-order