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
"""Scoring evaluation."""

import abc
import io
import os
from typing import Any
import langfun.core as lf
from langfun.core.eval import base
import pyglove as pg


class Scoring(base.Evaluation):
  """Base class of evaluations by scoring."""

  # CONSTANTS.
  SCORED_HTML = 'scored.html'

  @property
  def scored(self) -> list[tuple[Any, Any, float]]:
    """Returns a list of (input example, structured output, score)."""
    return self._scored

  @property
  def num_scored(self) -> int:
    """Returns the number of scored examples."""
    return len(self._scored)

  @property
  def score_rate(self) -> float:
    """Returns the score rate."""
    if self.num_completed == 0:
      return 0.0
    return self.num_scored / self.num_completed

  @property
  def scored_link(self) -> str:
    """Returns the matches page."""
    return self.link(os.path.join(self.dir, Scoring.SCORED_HTML))

  @property
  def avg_score(self) -> float:
    if self.num_scored == 0:
      return 0
    return sum([i[2] for i in self._scored]) / self.num_scored

  def _reset(self) -> None:
    super()._reset()
    self._scored = []

  def audit(self, example: Any, output: Any) -> None:
    score = self.score(example, output)
    self._scored.append((example, output, score))

  @abc.abstractmethod
  def score(self, example: Any, output: Any) -> float:
    """Scores the output against its input example."""

  def _status(self, progress: lf.concurrent.Progress) -> dict[str, Any]:
    del progress
    return {
        'Average Score': {self.avg_score},
        'Scored': '%.2f%% (%d/%d)' % (
            self.score_rate * 100,
            self.num_scored,
            self.num_completed,
        ),
        'Failed': '%.2f%% (%d/%d)' % (
            self.failure_rate * 100,
            self.num_failures,
            self.num_completed,
        ),
    }

  def summarize(self) -> pg.Dict:
    result = super().summarize()
    result.metrics.update(
        num_scored=self.num_scored,
        score_rate=self.score_rate,
        avg_score=self.avg_score,
    )
    return result

  def save(self) -> None:  # pylint: disable=redefined-builtin
    super().save()

    # Save scored.
    pg.save(
        self._html([self._render_result, self._render_scored]),
        os.path.join(self.dir, Scoring.SCORED_HTML),
        file_format='txt',
    )

  def _render_result_header(self, s: io.StringIO):
    super()._render_result_header(s)
    s.write('<td>Avg Score</td>')
    s.write('<td>Scored</td>')

  def _render_result_row(self, s: io.StringIO):
    super()._render_result_row(s)
    s.write(
        '<td><span style="color:blue">%.2f</span></td>' % self.avg_score
    )
    s.write(
        '<td><span style="color:red">%s</span>%s</td>'
        % (
            '%.2f%% ' % (self.score_rate * 100),
            '<a href="%s">(%d/%d)</a>'
            % (self.scored_link, self.num_scored, self.num_completed),
        )
    )

  def _render_scored(self, s: io.StringIO) -> None:
    """Formats the matched cases into html."""
    s.write('<h2> Scored </h2>')
    s.write('<div style="white-space:pre">\n')
    s.write(
        '<table style="border: 1px solid;">'
        '<tr class="header">'
        '<td>No.</td><td>Input</td><td>Output</td><td>Score</td>'
        '</tr>'
    )
    for i, (example, output, score) in enumerate(self.scored):
      bgcolor = 'white' if i % 2 == 0 else '#DDDDDD'
      s.write(f'<tr style="background-color: {bgcolor}"><td>{i + 1}</td>')
      input_str = pg.format(example, verbose=False)
      s.write(f'<td style="color:green;white-space:pre-wrap">{input_str}</td>')
      output_str = pg.format(output, verbose=False)
      s.write(f'<td style="color:blue;white-space:pre-wrap">{output_str}</td>')
      s.write(f'<td style="color:magenta;white-space:pre-wrap">{score}</td>')
      s.write('</tr>')
    s.write('</table></div>')