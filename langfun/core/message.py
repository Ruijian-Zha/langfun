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
"""Messages that are exchanged between users and agents."""

import contextlib
import io
from typing import Annotated, Any, Optional, Union

from langfun.core import modality
from langfun.core import natural_language
import pyglove as pg


class Message(natural_language.NaturalLanguageFormattable, pg.Object):
  """Message.

  ``Message`` is the protocol for users and the system to interact with
  LLMs. It consists of a text in the form of natural language, 
  an identifier of the sender, and a dictionary of Python values as structured
  meta-data.

  The subclasses of ``Message`` represent messages sent from different roles.
  Agents may use the roles to decide the orchastration logic.
  """

  #
  # Constants.
  #

  # PyGlove flag to allow modifications to the member attributes through
  # assignment.
  allow_symbolic_assignment = True

  # Constant that refers to the special key used to access the message itself
  # through `Message.get`.
  PATH_ROOT = ''

  # Constant that refers to the special key used to access the message text
  # through `Message.get`.
  PATH_TEXT = 'text'

  # Constant that refers to the special key for describing the structured
  # information extracted as the result of the response.
  PATH_RESULT = 'result'

  # Constant that tags an LM input.
  TAG_LM_INPUT = 'lm-input'

  # Constant that tags an LM response (before output_transform).
  TAG_LM_RESPONSE = 'lm-response'

  # Constant that tags an LM output message (after output_transform).
  TAG_LM_OUTPUT = 'lm-output'

  # Constant that tags a message that is generated by `LangFunc.render`
  TAG_RENDERED = 'rendered'

  # Constant that tags an transformed message.
  TAG_TRANSFORMED = 'transformed'

  #
  # Members
  #

  text: Annotated[str, 'The natural language representation of the message.']

  sender: Annotated[str, 'The sender of the message.']

  metadata: Annotated[
      dict[str, Any],
      (
          'The metadata associated with the message, '
          'which chould carry structured data, such as tool function input. '
          'It is a `pg.Dict` object whose keys can be accessed by attributes.'
      ),
  ] = pg.Dict()

  tags: Annotated[
      list[str],
      (
          'A list of tags associated with the message. '
          'Tags are useful for filtering messages along the source chain. '
      )
  ] = []

  # NOTE(daiyip): Explicit override __init__ for allowing metadata via **kwargs.
  @pg.explicit_method_override
  def __init__(
      self,
      text: str,
      *,
      # Default sender is specified in subclasses.
      sender: str | pg.object_utils.MissingValue = pg.MISSING_VALUE,
      metadata: dict[str, Any] | None = None,
      tags: list[str] | None = None,
      source: Optional['Message'] = None,
      # The rest are `pg.Object.__init__` arguments.
      allow_partial: bool = False,
      sealed: bool = False,
      root_path: pg.KeyPath | None = None,
      **kwargs
  ) -> None:
    """Constructor.

    Args:
      text: The text in the message.
      sender: The sender name of the message.
      metadata: Structured meta-data associated with this message.
      tags: Tags for the message.
      source: The source message of the current message.
      allow_partial: If True, the object can be partial.
      sealed: If True, seal the object from future modification (unless under a
        `pg.seal(False)` context manager). If False, treat the object as
        unsealed. If None, it's determined by `cls.allow_symbolic_mutation`.
      root_path: The symbolic path for current object. By default it's None,
        which indicates that newly constructed object does not have a parent.
      **kwargs: key/value pairs that will be inserted into metadata.
    """
    metadata = metadata or {}
    metadata.update(kwargs)
    super().__init__(
        text=text,
        metadata=metadata,
        tags=tags or [],
        sender=sender,
        allow_partial=allow_partial,
        sealed=sealed,
        root_path=root_path,
    )
    self._source = source

  @classmethod
  def from_value(cls, value: Union[str, 'Message']) -> 'Message':
    """Creates a message from a value or return value itself if a Message."""
    if isinstance(value, modality.Modality):
      return cls('{{object}}', object=value)
    if isinstance(value, Message):
      return value
    return cls(value)

  #
  # Unified interface for accessing text, result and metadata.
  #

  def set(self, key_path: str | pg.KeyPath, value: Any) -> None:
    """Sets a value by key path.

    This the unified interface for set values in Message.

    Examples::

      m = lf.AIMessage('foo', metadata=dict(x=dict(k=[0, 1]), y=2))
      m.set('text', 'bar')
      m.set('x.k[0]', 1)
      m.set('y', pg.MISSING_VALUE)   # Delete.
      assert m == lf.AIMessage('bar', metadata=dict(x=dict(k=[1, 1])))

    Args:
      key_path: A string or a ``pg.KeyPath`` object for locating the value to
        update. For example: `a.b`, `x[0].a`, `text` is a special key that sets
        the text of the message.
      value: The new value for the location.
    """
    if key_path == Message.PATH_TEXT:
      self.rebind({key_path: value}, raise_on_no_change=False)
    else:
      self.metadata.rebind({key_path: value}, raise_on_no_change=False)

  def get(self, key_path: str | pg.KeyPath, default: Any = None) -> Any:
    """Gets text or metadata by key path.

    This is the unified interface to query text or metadata values.

    Args:
      key_path: A string like 'a.x', 'b[0].y' to access metadata value in
        hierarchy. 'text' is a special key that returns the text of the message.
      default: The default value if the key path is not found in `self`.

    Returns:
      The value for the path if found, otherwise the default value.
    """
    if not key_path:
      return self
    if key_path == Message.PATH_TEXT:
      return self.text
    else:
      v = self.metadata.sym_get(key_path, default)
      return v.value if isinstance(v, pg.Ref) else v

  #
  # API for accessing the structured result and error.
  # `result` represents the structured output the message - like the return
  # value of a regular Python function. It is stored in metadata with a special
  # key `result`. By default it's None, and should be produced by transforms
  # upon the message text.

  @property
  def result(self) -> Any:
    """Gets the structured result of the message."""
    return self.get(Message.PATH_RESULT, None)

  @result.setter
  def result(self, value: Any) -> None:
    """Sets the structured result of the message."""
    self.set(Message.PATH_RESULT, value)

  #
  # Update and error tracking.
  #

  def _on_init(self):
    super()._on_init()
    self._updates = {}
    self._errors = []

  def _on_change(self, field_updates: dict[pg.KeyPath, pg.FieldUpdate]) -> None:
    super()._on_change(field_updates)
    self._updates.update(field_updates)

  @property
  def modified(self) -> bool:
    """Returns True if the message has been modified in current update scope."""
    return bool(self._updates)

  @property
  def updates(self) -> dict[pg.KeyPath, pg.FieldUpdate]:
    """Returns the updates of the message in current update scope."""
    return self._updates

  @property
  def has_errors(self) -> bool:
    """Returns True if there is an error in current update scope."""
    return bool(self._errors)

  @property
  def errors(self) -> list[Any]:
    """Returns the errors of the message in current update scope."""
    return self._errors

  @contextlib.contextmanager
  def update_scope(self):
    """Context manager to create a update scope."""
    accumulated_updates = self._updates
    accumulated_errors = self._errors

    try:
      self._updates, self._errors = {}, []
      yield
    finally:
      accumulated_updates.update(self._updates)
      self._updates = accumulated_updates

      accumulated_errors.extend(self._errors)
      self._errors = accumulated_errors

  def apply_updates(self, updates: dict[pg.KeyPath, pg.FieldUpdate]) -> None:
    """Updates this message with delta."""
    delta = {k: v.new_value for k, v in updates.items()}

    # Rebind will trigger _on_change, which inserts the updates
    # to current message' updates.
    self.rebind(delta, raise_on_no_change=False)

  #
  # API for supporting modalities.
  #

  def get_modality(
      self, var_name: str, default: Any = None, from_message_chain: bool = True
  ) -> modality.Modality | None:
    """Gets the modality object referred in the message.

    Args:
      var_name: The referred variable name for the modality object.
      default: default value.
      from_message_chain: If True, the look up will be performed from the
        message chain. Otherwise it will be performed in current message.

    Returns:
      A modality object if found, otherwise None.
    """
    obj = self.get(var_name, None)
    if isinstance(obj, modality.Modality):
      return obj
    elif obj is None and self.source is not None:
      return self.source.get_modality(var_name, default, from_message_chain)
    return default

  def referred_modalities(self) -> dict[str, modality.Modality]:
    """Returns modality objects attached on this message."""
    chunks = self.chunk()
    return {
        m.referred_name: m for m in chunks if isinstance(m, modality.Modality)
    }

  def chunk(self) -> list[str | modality.Modality]:
    """Chunk a message into a list of str or modality objects."""
    chunks = []

    def add_text_chunk(text_piece: str) -> None:
      if text_piece:
        chunks.append(text_piece)

    text = self.text
    chunk_start = 0
    ref_end = 0
    while chunk_start < len(text):
      ref_start = text.find(modality.Modality.REF_START, ref_end)
      if ref_start == -1:
        add_text_chunk(text[chunk_start:].strip())
        break

      var_start = ref_start + len(modality.Modality.REF_START)
      ref_end = text.find(modality.Modality.REF_END, var_start)
      if ref_end == -1:
        add_text_chunk(text[chunk_start:])
        break

      var_name = text[var_start:ref_end].strip()
      var_value = self.get_modality(var_name)
      if var_value is not None:
        add_text_chunk(text[chunk_start:ref_start].strip())
        chunks.append(var_value)
        chunk_start = ref_end + len(modality.Modality.REF_END)
    return chunks

  @classmethod
  def from_chunks(
      cls, chunks: list[str | modality.Modality], separator: str = '\n'
  ) -> 'Message':
    """Assembly a message from a list of string or modality objects."""
    fused_text = io.StringIO()
    ref_index = 0
    metadata = dict()

    for i, chunk in enumerate(chunks):
      if i > 0:
        fused_text.write(separator)
      if isinstance(chunk, str):
        fused_text.write(chunk)
      else:
        assert isinstance(chunk, modality.Modality), chunk
        var_name = f'obj{ref_index}'
        fused_text.write(modality.Modality.text_marker(var_name))
        # Make a reference if the chunk is already owned by another object
        # to avoid copy.
        metadata[var_name] = pg.maybe_ref(chunk)
        ref_index += 1
    return cls(fused_text.getvalue().strip(), metadata=metadata)

  #
  # API for testing the message types.
  #

  @property
  def from_user(self) -> bool:
    """Returns True if it's user message."""
    return isinstance(self, UserMessage)

  @property
  def from_agent(self) -> bool:
    """Returns True if it's agent message."""
    return isinstance(self, AIMessage)

  @property
  def from_system(self) -> bool:
    """Returns True if it's agent message."""
    return isinstance(self, SystemMessage)

  @property
  def from_memory(self) -> bool:
    return isinstance(self, MemoryRecord)

  #
  # Tagging
  #

  def tag(self, tag: str) -> None:
    if tag not in self.tags:
      with pg.notify_on_change(False):
        self.tags.append(tag)

  #
  # Message source chain.
  #

  @property
  def source(self) -> Optional['Message']:
    """Returns the source message."""
    return self._source

  @source.setter
  def source(self, source: 'Message') -> None:
    """Sets the source message."""
    self._source = source

  @property
  def root(self) -> 'Message':
    """Returns the root of this message."""
    root = self
    while root.source is not None:
      root = root.source
    return root

  def trace(self, tag: str | None = None) -> list['Message']:
    """Returns the chain of source messages filtered by tag."""
    message_chain = []
    current = self

    while current is not None:
      if tag is None or tag in current.tags:
        message_chain.append(current)
      current = current.source
    return list(reversed(message_chain))

  @property
  def lm_responses(self) -> list['Message']:
    """Returns a chain of LM responses starting from the first LM call."""
    return self.trace(Message.TAG_LM_RESPONSE)

  @property
  def lm_inputs(self) -> list['Message']:
    """Returns a chain of LM inputs starting from the first LM call."""
    return self.trace(Message.TAG_LM_INPUT)

  @property
  def lm_outputs(self) -> list['Message']:
    """Returns a chain of LM inputs starting from the first LM call."""
    return self.trace(Message.TAG_LM_OUTPUT)

  def last(self, tag: str) -> Optional['Message']:
    """Return the last message wih certain tag."""
    current = self
    while current is not None:
      if tag in current.tags:
        return current
      current = current.source
    return None

  @property
  def lm_response(self) -> Optional['Message']:
    """Returns the latest LM raw response."""
    return self.last(Message.TAG_LM_RESPONSE)

  @property
  def lm_input(self) -> Optional['Message']:
    """Returns the latest LM input."""
    return self.last(Message.TAG_LM_INPUT)

  @property
  def lm_output(self) -> Optional['Message']:
    """Returns the latest LM output."""
    return self.last(Message.TAG_LM_OUTPUT)

  #
  # Other methods.
  #

  def natural_language_format(self) -> str:
    return self.text

  def __eq__(self, other: Any) -> bool:
    if isinstance(other, str):
      return self.text == other
    if isinstance(other, self.__class__):
      return (self.text == other.text
              and self.sender == other.sender
              and self.metadata == other.metadata)
    return False

  def __hash__(self) -> int:
    return hash(self.text)

  def __getattr__(self, key: str) -> Any:
    if key not in self.metadata:
      raise AttributeError(key)
    v = self.metadata[key]
    return v.value if isinstance(v, pg.Ref) else v


#
# Messages of different roles.
#


@pg.use_init_args(['text', 'sender', 'metadata'])
class UserMessage(Message):
  """Message sent from a human user."""

  sender = 'User'


@pg.use_init_args(['text', 'sender', 'metadata'])
class AIMessage(Message):
  """Message sent from an agent."""

  sender = 'AI'


@pg.use_init_args(['text', 'sender', 'metadata'])
class SystemMessage(Message):
  """Message sent from the system or environment."""

  sender = 'System'


@pg.use_init_args(['text', 'sender', 'metadata'])
class MemoryRecord(Message):
  """Message used as a memory record."""

  sender = 'Memory'
