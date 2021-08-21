from __future__ import annotations

import sys
from typing import Tuple, Union, Iterable, Final, final, Optional, Dict, Annotated, List
from abc import abstractmethod, ABC
from pkg_resources import resource_filename

vec3 = Union[str, Iterable]
vec4 = Union[str, Iterable]


def to_glsl_vec(vec, n: int) -> str:
    if n < 2 or n > 4:
        raise ValueError(f"Bad GLSL vector dimension {n}. GLSL supports only 2, 3 and 4.")
    if isinstance(vec, str):
        return vec
    elif isinstance(vec, Iterable):
        answer = f"vec{n}("
        for i in vec:
            answer += str(i) + ", "
        return answer[:-2] + ")"
    else:
        raise ValueError(f"Cannot convert '{vec}' to GLSL's vec{n}")


class SDF(ABC):
    SD_FUNC_NAME: Final[str] = "sdist"

    __generated_sdfs: List[SDF] = []

    @staticmethod
    def generated_sdfs() -> List[SDF]:
        return SDF.__generated_sdfs

    def __init__(self):
        self.id = len(SDF.__generated_sdfs)
        SDF.__generated_sdfs.append(self)
        self.parameters: Dict[Annotated[str, "param_name"],
                              Union[Tuple[Annotated[str, "param_type"], Annotated[str, "param_value"]],
                                    SDF]] = {}
        self.translation: Optional[str] = "vec3(0, 0, 0)"
        self.rotation: Optional[str] = "vec4(0, 0, 0, 1)"
        self.scale: str = "1"

    @final
    def __getitem__(self, item) -> str:
        if item == 0:
            return self.glsl_struct_name()
        if item == 1:
            return self.initialisation()
        raise KeyError(f"Undefined {self}[{item}]")

    def glsl_struct_name(self) -> str:
        """Returns SDF type name in GLSL code. Equals ``f"SDF{self.id}"``"""
        return f"SDF{self.id}"

    @abstractmethod
    def sdist(self) -> str:
        pass

    @final
    def declaration(self) -> str:
        """SDF declaration in shader."""
        return f"SDFType({self.glsl_struct_name()},\n" \
               "{\n" + "".join(self.parameters[param][0] + " " + param + ";\n" for param in sorted(self.parameters)) + \
                                                                                            "Transform t;\n},\n" \
               "{\n" + self.sdist() + "\n})"

    @final
    def initialisation(self) -> str:
        """SDF initialisation in ``sdScene()``"""
        return f"{self.glsl_struct_name()}(" \
               + "".join(self.parameters[param][1] + ", " for param in sorted(self.parameters)) \
               + f"Transform({self.rotation}, {self.translation}, {self.scale}))"

    @final
    def translated(self, tr: vec3) -> SDF:
        if self.translation is None:
            self.translation = to_glsl_vec(tr, 3)
        else:
            self.translation = f"({self.translation} + {to_glsl_vec(tr, 3)})"
        return self

    @final
    def rotated(self, u: vec3, angle) -> SDF:
        return self.rotated_quaternion(f"vec4({to_glsl_vec(u, 3)} * cos(({angle}) / 2), sin(({angle}) / 2))")

    @final
    def rotated_quaternion(self, q: vec4) -> SDF:
        # TODO quaternions multiplication, de-facto rotation composition instead of overriding previous rotation
        self.rotation = to_glsl_vec(q, 4)
        return self

    @final
    def scaled(self, k) -> SDF:
        self.scale = f"({self.scale} * ({k}))"
        return self


class Scene:
    def __init__(self, name: Optional[str] = None):
        self.name: Optional[str] = name
        self.sdf: Optional[SDF] = None
        if "--scene-name-only" in sys.argv:
            print(self.name if self.name is not None else "Unnamed scene")
            exit(0)

    def set_sdf(self, sdf: SDF) -> None:
        self.sdf: SDF = sdf

    def process(self) -> None:
        """Generates and prints GLSL fragment shader of scene."""
        if self.sdf is None:
            self.sdf = Emptiness()
        sdf_types: str = ''.join(sdf.declaration() + ";\n" for sdf in SDF.generated_sdfs())
        sdscene: str = f"return sdist(p, {self.sdf.initialisation()});"
        with open(resource_filename("raymarching", "raymarching.frag")) as template:
            src = template.readline()
            src += "#define TEMPLATE_SDFTYPES \\\n" + sdf_types.replace("\n", "\\\n") + "\n"
            src += "#define TEMPLATE_SDSCENE \\\n" + sdscene.replace("\n", "\\\n") + "\n"
            src += template.read()
            print(src)


class Emptiness(SDF):
    def sdist(self) -> str:
        return "return INF;"


class Sphere(SDF):
    def sdist(self) -> str:
        return "return length(p) - 1.0;"


class AABBox(SDF):
    def __init__(self, r: vec3):
        super().__init__()
        self.parameters |= {"r": ("vec3", to_glsl_vec(r, 3))}

    def sdist(self) -> str:
        return "vec3 d = abs(p) - o.r; return min(max(d.x, max(d.y, d.z)), 0.0) + length(max(d, 0.0));"


class Plane(SDF):
    def sdist(self) -> str:
        return "return abs(p.y);"


class Cylinder(SDF):
    def __init__(self, radius, height2):
        super().__init__()
        self.parameters |= {
            "radius": ("float", str(radius)),
            "height2": ("float", str(height2)),
        }

    def sdist(self) -> str:
        return """vec2 d = vec2(length(p.xz) - o.radius, abs(p.y) - o.height2); 
                  return min(max(d.x, d.y), 0.0) + length(max(d, 0.0));"""


class SDFOperator(SDF):
    def __init__(self, func: str, *args: SDF):
        super().__init__()
        self.objects: Tuple[SDF] = args
        self.parameters |= {f"o{sdf.id}": sdf for sdf in args}
        self.func: str = func

    def sdist(self) -> str:
        answer = f"return {self.func}("
        for o in self.objects[:-2]:
            answer += f"sdist(p, o.o{o.id}), {self.func}("
        return answer + f"sdist(p, o.o{self.objects[-2].id}), sdist(p, o.o{self.objects[-1].id})" + \
               ")" * (len(self.objects) - 1) + ";"


class Intersection(SDFOperator):
    def __init__(self, *args: SDF):
        super().__init__("max", *args)


class Union(SDFOperator):
    def __init__(self, *args: SDF):
        super().__init__("min", *args)


class SmoothUnion(SDFOperator):
    def __init__(self, k, *args: SDF):
        super().__init__("smin", *args)
        self.parameters |= {
            "k": ("float", str(k))
        }

    def sdist(self) -> str:
        answer = f"return {self.func}("
        for o in self.objects[:-2]:
            answer += f"sdist(p, o.o{o.id}), {self.func}("
        return answer + f"sdist(p, o.o{self.objects[-2].id}), sdist(p, o.o{self.objects[-1].id})" + \
               ", o.k)" * (len(self.objects) - 1) + ";"


class Difference(SDF):
    def __init__(self, o1: SDF, o2: SDF):
        super().__init__()
        self.parameters |= {
            "o1": o1,
            "o2": o2,
        }

    def sdist(self):
        return "return max(sdist(p, o.o1), -sdist(p, o.o2));"
