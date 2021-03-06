from abc import ABC, abstractmethod
from owrx.modes import Modes
from owrx.config import Config
from owrx.form.converter import Converter, NullConverter, IntConverter, FloatConverter, EnumConverter
from enum import Enum


class Input(ABC):
    def __init__(self, id, label, infotext=None, converter: Converter = None):
        self.id = id
        self.label = label
        self.infotext = infotext
        self.converter = self.defaultConverter() if converter is None else converter

    def defaultConverter(self):
        return NullConverter()

    def bootstrap_decorate(self, input):
        infotext = "<small>{text}</small>".format(text=self.infotext) if self.infotext else ""
        return """
            <div class="form-group row">
                <label class="col-form-label col-form-label-sm col-3" for="{id}">{label}</label>
                <div class="col-9 p-0">
                    {input}
                    {infotext}
                </div>
            </div>
        """.format(
            id=self.id, label=self.label, input=input, infotext=infotext
        )

    def input_classes(self):
        return " ".join(["form-control", "form-control-sm"])

    @abstractmethod
    def render_input(self, value):
        pass

    def render(self, config):
        value = config[self.id] if self.id in config else None
        return self.bootstrap_decorate(self.render_input(self.converter.convert_to_form(value)))

    def parse(self, data):
        return {self.id: self.converter.convert_from_form(data[self.id][0])} if self.id in data else {}


class TextInput(Input):
    def render_input(self, value):
        return """
            <input type="text" class="{classes}" id="{id}" name="{id}" placeholder="{label}" value="{value}">
        """.format(
            id=self.id, label=self.label, classes=self.input_classes(), value=value
        )


class NumberInput(Input):
    def __init__(self, id, label, infotext=None, append="", converter: Converter = None):
        super().__init__(id, label, infotext, converter=converter)
        self.step = None
        self.append = append

    def defaultConverter(self):
        return IntConverter()

    def render_input(self, value):
        if self.append:
            append = """
                <div class="input-group-append">
                    <span class="input-group-text">{append}</span>
                </div>
            """.format(
                append=self.append
            )
        else:
            append = ""

        return """
            <div class="input-group input-group-sm">
                <input type="number" class="{classes}" id="{id}" name="{id}" placeholder="{label}" value="{value}" {step}>
                {append}
            </div>
        """.format(
            id=self.id,
            label=self.label,
            classes=self.input_classes(),
            value=value,
            step='step="{0}"'.format(self.step) if self.step else "",
            append=append,
        )


class FloatInput(NumberInput):
    def __init__(self, id, label, infotext=None, converter: Converter = None):
        super().__init__(id, label, infotext, converter=converter)
        self.step = "any"

    def defaultConverter(self):
        return FloatConverter()


class LocationInput(Input):
    def render_input(self, value):
        return """
            <div class="row">
                {inputs}
            </div>
            <div class="row">
                <div class="col map-input" data-key="{key}" for="{id}"></div>
            </div>
        """.format(
            id=self.id,
            inputs="".join(self.render_sub_input(value, id) for id in ["lat", "lon"]),
            key=Config.get()["google_maps_api_key"],
        )

    def render_sub_input(self, value, id):
        return """
            <div class="col">
                <input type="number" class="{classes}" id="{id}" name="{id}" placeholder="{label}" value="{value}" step="any">
            </div>
        """.format(
            id="{0}-{1}".format(self.id, id),
            label=self.label,
            classes=self.input_classes(),
            value=value[id],
        )

    def parse(self, data):
        return {self.id: {k: float(data["{0}-{1}".format(self.id, k)][0]) for k in ["lat", "lon"]}}


class TextAreaInput(Input):
    def render_input(self, value):
        return """
            <textarea class="{classes}" id="{id}" name="{id}" style="height:200px;">{value}</textarea>
        """.format(
            id=self.id, classes=self.input_classes(), value=value
        )


class CheckboxInput(Input):
    def __init__(self, id, label, checkboxText, infotext=None):
        super().__init__(id, label, infotext=infotext)
        self.checkboxText = checkboxText

    def render_input(self, value):
        return """
          <div class="{classes}">
            <input class="form-check-input" type="checkbox" id="{id}" name="{id}" {checked}>
            <label class="form-check-label" for="{id}">
              {checkboxText}
            </label>
          </div>
        """.format(
            id=self.id,
            classes=self.input_classes(),
            checked="checked" if value else "",
            checkboxText=self.checkboxText,
        )

    def input_classes(self):
        return " ".join(["form-check", "form-control-sm"])

    def parse(self, data):
        return {self.id: self.id in data and data[self.id][0] == "on"}


class Option(object):
    # used for both MultiCheckboxInput and DropdownInput
    def __init__(self, value, text):
        self.value = value
        self.text = text


class MultiCheckboxInput(Input):
    def __init__(self, id, label, options, infotext=None):
        super().__init__(id, label, infotext=infotext)
        self.options = options

    def render_input(self, value):
        return "".join(self.render_checkbox(o, value) for o in self.options)

    def checkbox_id(self, option):
        return "{0}-{1}".format(self.id, option.value)

    def render_checkbox(self, option, value):
        return """
          <div class="{classes}">
            <input class="form-check-input" type="checkbox" id="{id}" name="{id}" {checked}>
            <label class="form-check-label" for="{id}">
              {checkboxText}
            </label>
          </div>
        """.format(
            id=self.checkbox_id(option),
            classes=self.input_classes(),
            checked="checked" if option.value in value else "",
            checkboxText=option.text,
        )

    def parse(self, data):
        def in_response(option):
            boxid = self.checkbox_id(option)
            return boxid in data and data[boxid][0] == "on"

        return {self.id: [o.value for o in self.options if in_response(o)]}

    def input_classes(self):
        return " ".join(["form-check", "form-control-sm"])


class ServicesCheckboxInput(MultiCheckboxInput):
    def __init__(self, id, label, infotext=None):
        services = [Option(s.modulation, s.name) for s in Modes.getAvailableServices()]
        super().__init__(id, label, services, infotext)


class Js8ProfileCheckboxInput(MultiCheckboxInput):
    def __init__(self, id, label, infotext=None):
        profiles = [
            Option("normal", "Normal (15s, 50Hz, ~16WPM)"),
            Option("slow", "Slow (30s, 25Hz, ~8WPM"),
            Option("fast", "Fast (10s, 80Hz, ~24WPM"),
            Option("turbo", "Turbo (6s, 160Hz, ~40WPM"),
        ]
        super().__init__(id, label, profiles, infotext)


class DropdownInput(Input):
    def __init__(self, id, label, options, infotext=None, converter: Converter = None):
        try:
            isEnum = issubclass(options, DropdownEnum)
        except TypeError:
            isEnum = False
        if isEnum:
            self.options = [o.toOption() for o in options]
            if converter is None:
                converter = EnumConverter(options)
        else:
            self.options = options
        super().__init__(id, label, infotext=infotext, converter=converter)

    def render_input(self, value):
        return """
            <select class="{classes}" id="{id}" name="{id}">{options}</select>
        """.format(
            classes=self.input_classes(), id=self.id, options=self.render_options(value)
        )

    def render_options(self, value):
        options = [
            """
                <option value="{value}" {selected}>{text}</option>
            """.format(
                text=o.text,
                value=o.value,
                selected="selected" if o.value == value else "",
            )
            for o in self.options
        ]
        return "".join(options)


class DropdownEnum(Enum):
    def toOption(self):
        return Option(self.name, str(self))
