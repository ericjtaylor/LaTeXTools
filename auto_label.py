import re

import sublime
import sublime_plugin

_command_mapping = {
    "part": "part",
    "chapter": "cha",
    "section": "sec",
    "subsection": "sub",
    "subsubsection": "ssub",
    "paragraph": "par",
}

_env_mapping = {
    "figure": "fig",
    "table": "tab",
    "listing": "lst",
}

_char_replace = {
    "ü": "ue",
    "ä": "ae",
    "ö": "oe",
    "ß": "ss",
}

_RE_FIND_SECTION = re.compile(
    r"\\(?P<command>" + "|".join(_command_mapping.keys()) + "|caption)"
    r"(?:\[[^\]]*\])*"
    r"\{(?P<content>[^\}]+)\}"
)

_RE_IS_LABEL_BEFORE = re.compile(
    r"(?P<brace>\{)?lebal\\"
)

_RE_FIND_ENV_END = r"\\end{(\w+)}"


def _create_label_content(command_content):
    label_content = []
    is_underscore = False
    for c in command_content:
        c = c.lower()
        if re.match("[a-z0-9]", c):
            label_content.append(c)
            is_underscore = False
        elif c in _char_replace:
            label_content.append(_char_replace[c])
            is_underscore = False
        elif not is_underscore:
            label_content.append("_")
            is_underscore = True
    label_content = "".join(label_content)
    return label_content


def _find_label_type_by_env(view, pos):
    env_end_reg = view.find(_RE_FIND_ENV_END, pos)
    if env_end_reg == sublime.Region(-1):
        return
    env_end_str = view.substr(env_end_reg)
    m = re.match(_RE_FIND_ENV_END, env_end_str)
    if not m:
        return
    label_type = _env_mapping.get(m.group(1))
    return label_type


def _find_label_content(view, pos, find_region):
    label_type = "???"
    find_region_str = view.substr(find_region)
    m = _RE_FIND_SECTION.search(find_region_str)
    if m:
        command_content = m.group("content")
        label_content = _create_label_content(command_content)

        command_name = m.group("command")
        if command_name == "caption":
            label_type = _find_label_type_by_env(view, pos) or label_type
        else:
            label_type = _command_mapping.get(command_name, label_type)
    else:
        label_content = "label"

    return label_type, label_content


def _create_surrounding_text(view, pos):
    line_before = view.substr(sublime.Region(view.line(pos).a, pos))[::-1]
    m = _RE_IS_LABEL_BEFORE.match(line_before)
    if not m:
        before_text, after_text = "\\label{", "}"
    elif not m.group("brace"):
        before_text, after_text = "{", "}"
    else:
        before_text = after_text = ""
    return before_text, after_text


class LatextoolsAutoInsertLabelCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        for sel in view.sel():
            pos = sel.b
            line_above = view.line(view.line(pos).a - 1)
            find_region = sublime.Region(line_above.a, pos)

            label_type, label_content = _find_label_content(
                view, pos, find_region)

            before_text, after_text = _create_surrounding_text(view, pos)

            # if we only have one selection insert it as a snippet
            # else insert the label as it is
            if len(view.sel()) == 1:
                snippet = (
                    "{before_text}"  # leading \label{
                    "${{1:{label_type}}}:${{2:{label_content}}}"
                    "{after_text}"  # trailing }
                    "$0"
                    .format(**locals())
                )
                view.run_command("insert_snippet", {"contents": snippet})
            else:
                content = (
                    "{before_text}"  # leading \label{
                    "{label_type}:{label_content}"
                    "{after_text}"  # trailing }
                    .format(**locals())
                )
                view.insert(edit, pos, content)
