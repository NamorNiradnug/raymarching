#version 440

#ifndef TEMPLATE_SDSCENE
#define TEMPLATE_SDSCENE return INF;
#endif

#ifndef TEMPLATE_SDFTYPES
#define TEMPLATE_SDFTYPES
#endif

vec3 rotated(vec3 p, vec4 q)
{
    return p + 2.0 * cross(q.xyz, cross(q.xyz, p) + q.w * p);
}

#define SDFType(name, params, sdf) \
    struct name params; \
    float sdistNoTransform(vec3 p, name o) sdf \
    float sdist(vec3 p, name o) \
    { \
        return sdistNoTransform(rotated(p - o.t.translation, o.t.rotation) / o.t.scale, o) * o.t.scale; \
    }


in vec2 uv;

out vec4 fragColor;

const vec3 UP = vec3(0.0, 1.0, 0.0);
const float INF = 1.0 / 0.0;
const vec3 INF3 = vec3(INF, INF, INF);

uniform float TIME;
uniform float WIDTH;
uniform float HEIGHT;

uniform bool SHADOWS_ENABLED = true;
uniform float RENDER_DISTANCE = 40;
uniform float MIN_HIT_DIST = 0.001;
#define EPSILON MIN_HIT_DIST * 2.0
uniform int MAX_STEPS = 400;

uniform struct Camera
{
    vec3 position;
    vec3 direction;
    float fov2_tan;
} camera;

uniform vec3 sun;

struct Transform
{
    vec4 rotation;
    vec3 translation;
    float scale;
};

#define sq(a) (a * a)

float smin(float a, float b, float k)
{
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

TEMPLATE_SDFTYPES

float sdScene(vec3 p)
{
    TEMPLATE_SDSCENE
}

vec3 normalAtPoint(vec3 p)
{
    return normalize(vec3(
        sdScene(vec3(p.x + EPSILON, p.y, p.z)) - sdScene(vec3(p.x - EPSILON, p.y, p.z)),
        sdScene(vec3(p.x, p.y + EPSILON, p.z)) - sdScene(vec3(p.x, p.y - EPSILON, p.z)),
        sdScene(vec3(p.x, p.y, p.z + EPSILON)) - sdScene(vec3(p.x, p.y, p.z - EPSILON))
    ));
}

vec3 raymarch(vec3 p, vec3 ray_dir, float max_dist)
{
    float depth = 0.0;
    for (int _ = 0; depth < max_dist && _ < MAX_STEPS; ++_)
    {
        vec3 pos = p + ray_dir * depth;
        float scene_dist = abs(sdScene(pos));
        if (scene_dist < MIN_HIT_DIST)
        {
            if (scene_dist < MIN_HIT_DIST / 10.0)
            {
                pos -= ray_dir * MIN_HIT_DIST / 2.0;
            }
            return pos;
        }
        depth += scene_dist;
    }
    return INF3;
}

float lightCoef(vec3 pos, vec3 normal)
{
    float light = dot(sun, normal);
    if (SHADOWS_ENABLED)
    {
        vec3 hit_p = raymarch(pos + normal * MIN_HIT_DIST, sun, 3 * RENDER_DISTANCE);
        if (length(hit_p - pos) > MIN_HIT_DIST * 2 && hit_p != INF3)
        {
           light /= 2;
        }
    }
    return light;
}

vec3 hitColor(vec3 p)
{
    vec3 n = normalAtPoint(p);
    return vec3(1, 1, 1) * lightCoef(p, n);
}

vec3 rayDirection()
{
    vec2 screen_coord = uv;
    screen_coord.x *= WIDTH / HEIGHT;
    vec2 offsets = screen_coord * camera.fov2_tan;
    vec3 right = normalize(cross(camera.direction, UP));
    vec3 up = cross(right, camera.direction);
    return normalize(camera.direction + right * offsets.x + up * offsets.y);
}

vec3 skyColor(vec3 direction)
{
    float light_dot = dot(direction, sun);
    if (light_dot > 0.995)
    {
        float a = normalize(0.0);
        return vec3(1.0, 1.0, 0.5);
    }
    return mix(vec3(0.5, 0.5, 1.0), vec3(0.7, 0.7, 1.0), light_dot * 0.5 + 0.5);
}

void main()
{
    vec3 ray_dir = rayDirection();
    vec3 hit = raymarch(camera.position, ray_dir, RENDER_DISTANCE);
    if (hit != INF3)
    {
        fragColor = vec4(hitColor(hit), 1.0);
    }
    else
    {
        fragColor = vec4(skyColor(ray_dir), 1.0);
    }
}
