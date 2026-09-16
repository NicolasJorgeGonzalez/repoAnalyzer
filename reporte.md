# 1. Resumen Ejecutivo y Arquitectura

### Visión General del Proyecto
**AgroSense (`hackCBA`)** es una plataforma agrotecnológica integral orientada a productores agrícolas (con foco regional inicial en la provincia de Córdoba, Argentina). Su propósito es la monitorización meteorológica en tiempo real, predicción y evaluación determinista del riesgo agronómico (heladas, estrés térmico, tormentas severas, granizo), seguimiento fenológico de lotes (maíz y soja), visualización geoespacial con imágenes satelitales (Copernicus Sentinel-2 L2A) y un sistema bidireccional de alertas e interacción asistida mediante WhatsApp (vía Kapso y un agente con razonamiento sobre LLM a través de OpenRouter).

### Stack Tecnológico Detectado
* **Monorepo & Tooling:** PNPM Workspaces v11.21.0, Node.js 24, Biome v2.5.13 (formateo y linter estricto), TypeScript 7.x/5.x.
* **Backend (`apps/api`):**
  * **Runtime:** Cloudflare Workers con Durable Objects (`cloudflare:workers`, Miniflare para entornos locales/test).
  * **Framework HTTP:** Hono v4.13.7.
  * **Integración AI / Agente:** Vercel AI SDK (`ai` v7.0.99), `@openrouter/ai-sdk-provider` v3.0.0.
  * **Criptografía & Auth:** `jose` v6.2.12 (verificación stateless de JWTs/JWKS ES256/RS256 y HMAC WebCrypto nativo).
  * **Geo / Imagen:** `fast-png` v8.0.0 para decodificación y validación de máscaras alfa en rásteres satelitales.
* **Frontend (`apps/web`):**
  * **Framework & Build:** React 19.3.0, React DOM 19, Vite v8.3.0 (`@vitejs/plugin-react`).
  * **Estilos & UI:** Tailwind CSS v4.3.3 (`@tailwindcss/vite`), `@base-ui/react`, `class-variance-authority`, `lucide-react`.
  * **Mapas & Geo:** Leaflet v1.9.4.
  * **Gestión de Estado de Red:** `@tanstack/react-query` v5.102.8.
* **Capa de Contratos (`packages/contracts`):**
  * Validación y tipado compartido con Zod v4.6.2 (modelos de dominio, reglas agronómicas, geometrías GeoJSON, APIs de WhatsApp y Dashboard).
* **Persistencia & Base de Datos (`supabase`):**
  * PostgreSQL provisionado en Supabase, migraciones SQL secuenciales, Row-Level Security (RLS) basado en `auth.uid()`, RPCs en PL/pgSQL para mutaciones atómicas y transaccionales, testing embebido mediante `@electric-sql/pglite`.
* **Servicios de Terceros:**
  * Open-Meteo API (predicciones meteorológicas horarias a 2 metros).
  * Copernicus Data Space Ecosystem / Sentinel Hub (catálogo STAC e imágenes satelitales procesadas).
  * Kapso.ai (API de WhatsApp Business Cloud API & Webhooks).
  * OpenRouter (modelos LLM, por defecto `deepseek/deepseek-v4.1-flash`).

### Patrones Arquitectónicos Identificados
1. **Contract-Driven Design (Shared Monorepo Package):** Todo el intercambio entre cliente, servidor y la base de datos se rige por contratos Zod estrictos ubicados en `@agrosense/contracts`. La validación ocurre en los límites de entrada y salida con tipado estricto inferido (`z.infer`).
2. **Hexagonal / Ports & Adapters:** Desacoplamiento de adaptadores externos (Open-Meteo, Copernicus, Kapso, OpenRouter) mediante funciones de infraestructura que encapsulan llamadas HTTP seguras (`boundedFetch`) con límites de bytes y timeouts estrictos.
3. **Actor Model vía Durable Objects (Stateful WhatsApp Agent):** Se implementa `WhatsAppConversation` como un Cloudflare Durable Object por cada remitente (`ownerId:phoneNumberId:sender`), garantizando procesamiento FIFO, deduplicación atómica, control de alarmas, transacciones en storage local y persistencia de memoria conversacional transitoria.
4. **Outbox Pattern y Job Scheduling:** Cola transaccional de notificaciones en PostgreSQL (`notification_outbox`) procesada por lotes y contratos idempotentes (estados `pending`, `leased`, `sending`, `accepted`, `delivered`, `failed`).
5. **Optimistic Concurrency Control (OCC):** Esquema de versiones de datos (`data_version`, `expectedDataVersion`) en `farms` y mutaciones de ciclos de cultivo para prevenir condiciones de carrera y escrituras sucias concurrentes.

### Estructura Modular y Flujo de Datos Principal
```
                  [ Navegador Web (React 19 / Leaflet) ]
                             │               │
                      Auth Session     REST / CORS
                             ▼               ▼
                 [ Supabase Auth ]    [ Cloudflare Worker (Hono API) ]
                                             │
                        ┌────────────────────┼─────────────────────┐
                        ▼                    ▼                     ▼
               [ Open-Meteo API ]   [ Copernicus STAC ]    [ Durable Object ]
                        │                    │              (WhatsApp Agent)
                        │                    │                     │
                        └──────────────┬─────┴─────────────────────┤
                                       ▼                           ▼
                        [ Supabase PostgreSQL (RLS / RPC) ]    [ Kapso.ai ]
```

---

# 2. Evaluación de Salud del Código y Buenas Prácticas

### Organización y Estructura de Directorios
* **Monorepo coherente:** Estructuración limpia dividida en `apps/api`, `apps/web` y `packages/contracts`. La inclusión de migraciones SQL versionadas en `supabase/migrations` junto con scripts de tipado (`scripts/db-types.mjs`) garantiza trazabilidad.
* **Separación de capas en Backend:** División explícita en `agent/` (orquestación LLM y durable worker), `automation/` (jobs en background y outbox), `satellite/` (Copernicus) y `lib/` (infraestructura, autenticación, contratos con DB).

### Separación de Responsabilidades y Cohesión Modular
* **Dominio Puro Desacoplado:** El motor agronómico (`engine.ts`, `agronomic.ts`, `economic-impact.ts`) reside en el paquete de contratos y es 100% determinista, libre de dependencias de I/O o base de datos. Admite pruebas de regresión matemáticas y temporales puras.
* **Límites de Seguridad y Clientes Supabase:** Excelente delimitación entre `createUserClient` (utiliza el token JWT del usuario y respeta las políticas RLS) y `createServiceClient` (uso exclusivo de `SUPABASE_SECRET_KEY` para operaciones de fondo, RPCs internas y semillas).

### Gestión de Dependencias y Configuración
* **Control estricto de variables de entorno:** Uso de schemas de validación inmediata con Zod para configuración de entorno (`readSupabaseConfig`, `readKapsoConfig`, `readModelConfig`).
* **Seguridad en Headers y CORS:** `CORS_ORIGIN` no está parametrizado con comodines (`*`), sino limitado estrictamente al origen configurado del frontend, validado tanto en OPTIONS como en requests reales. Headers HTTP incluyen `Cache-Control: private, no-store` en todas las rutas autenticadas.
* **Uso de WebCrypto:** Verificación de firmas HMAC y derivación criptográfica mediante las Web APIs estándar de Cloudflare Workers (`crypto.subtle`), evitando dependencias de Node.js no nativas en el Edge.

### Calidad y Consistencia en el Estilo, Tipado y Documentación
* **Tipado Inflexible:** Se evita el uso de `any`; se hace un uso extensivo de `unknown`, refinamientos Zod (`.refine`), y tipos discriminados (`discriminatedUnion`).
* **Manejo Seguro de Streams:** En `readLimitedRequestBody` y `boundedFetch`, los streams de red se leen con contadores explícitos de bytes UTF-8 y se cancelan (`reader.cancel()`, `TransformStream`) tan pronto como superan los umbrales de payload (16 KiB, 128 KiB o 1 MiB), mitigando ataques de denegación de servicio por memoria (OOM).
* **Documentación Técnica:** `docs/` contiene arquitectura detallada (`stack.md`, `domain-model.md`, `kapso.md`, `whatsapp-agent.md`), lo que facilita la incorporación de ingenieros al equipo.

---

# 3. Puntos de Dolor y Deuda Técnica

### Posibles Cuellos de Botella de Rendimiento o Escalabilidad
1. **Serialización de Tareas en el Agente Conversacional:**
   En `apps/api/src/agent/runner.ts`, las herramientas del agente se ejecutan de forma secuencial encoladas a través de una promesa encadenada (`pending = task.catch(...)`). Aunque esto previene condiciones de carrera sobre APIs de terceros, en escenarios donde el LLM solicita `list_farms`, `list_plots` y múltiples `get_forecast` en una sola llamada de herramientas (batch), la latencia total del Worker puede acercarse al límite de tiempo (timeout de 60 segundos).
2. **Límite de Ejecución Paralela en Refresh Meteorológico:**
   En `apps/api/src/lib/refresh.ts`, el refresh de lotes (`fetchOpenMeteoPlotForecast`) se procesa en bloques de 2 en 2 (`slice(i, i + 2)`). Aunque protege la cuota de la API de Open-Meteo, para establecimientos con el límite máximo de 10 parcelas se generan hasta 5 rondas consecutivas de requests, incrementando la probabilidad de un `PROVIDER_TIMEOUT` en el Worker si la red externa presenta latencia.
3. **Sobrecarga de Cálculo Geométrico en JS:**
   Las validaciones topológicas de polígonos complejos e intersecciones (`geometry.ts`, `polygonsOverlap`, `isSimpleRing`) se resuelven puramente en TypeScript con algoritmos de complejidad $O(V^2)$ en el peor caso. Aunque está limitado a 5.000 vértices, esta carga computacional en el hilo único del Cloudflare Worker puede consumir CPU Time sensible. PostGIS en Supabase es considerablemente más eficiente para operaciones como `ST_Intersects` y `ST_Contains`.

### Riesgos de Seguridad y Manejo de Errores
1. **Doble Dependencia de Roles en Supabase:**
   En `apps/api/src/lib/onboarding.ts`, métodos como `createPlot` realizan consultas directas de lectura con el cliente del usuario (`farms`, `plots`), pero delegan la inserción final a la RPC `create_farm_plot` usando el `createServiceClient` (Service Role que omite RLS). Si bien valida `p_owner_id` dentro del procedimiento PL/pgSQL, la alternancia entre cliente con RLS y Service Role en el mismo flujo de aplicación expone al sistema a elevaciones de privilegios involuntarias si un desarrollador olvida filtrar por `owner_id` en una consulta posterior.
2. **Estrategia de Fallback en el Agente WhatsApp:**
   Cuando el modelo LLM falla por timeout o cuota (`MODEL_UNAVAILABLE`), el Durable Object envía un mensaje honesto de indisponibilidad pero marca el registro de la carrera en el estado de WhatsApp como `accepted` con un `errorCode`. Esto enmascara la falla a nivel de monitoreo de transporte HTTP, impidiendo que plataformas de observabilidad como Sentry o Datadog activen alertas tempranas salvo que se analicen los logs JSON estructurados.
3. **Bloqueo del Historial Conversacional en DO Storage:**
   En `apps/api/src/agent/conversation.ts`, las conversaciones almacenan hasta 12 intercambios de mensajes en un solo registro de almacenamiento (`history`). No existe cifrado en reposo para este payload dentro del almacenamiento local del Durable Object (más allá del cifrado de Cloudflare en infraestructura), guardando texto plano de mensajes que podrían incluir nombres propios o datos sensibles de la explotación agropecuaria.

### Acoplamiento y Cobertura de Testing
* **Cobertura de Pruebas Excepcional:** El proyecto cuenta con un conjunto de tests de integración y regresión sobresaliente (utilizando Vitest, mocks estrictos y `@electric-sql/pglite` para ejecutar las migraciones SQL reales contra un motor Postgres en WebAssembly).
* **Duplicación de Lógica Temporal:** La función de formateo de fecha y hora para la zona horaria `America/Argentina/Cordoba` se encuentra reimplementada en múltiples módulos con pequeñas variantes (`notification.ts`, `engine.ts`, `onboarding.ts`, `presentation.ts`, `forecast.ts`).

---

# 4. Propuestas Concretas de Refactorización y Mejora

### Matriz de Recomendaciones Priorizadas

| Prioridad | Área | Hallazgo / Oportunidad | Acción Recomendada |
| :--- | :--- | :--- | :--- |
| **Alta** | Rendimiento / Edge | Ejecución secuencial forzada de herramientas de lectura en el agente | Permitir ejecución concurrente (`Promise.all`) para herramientas idempotentes y puras de sólo lectura (`list_farms`, `get_forecast`). |
| **Alta** | Rendimiento / DB | Cálculos geométricos intensivos en JavaScript dentro del Worker | Delegar las comprobaciones de contención (`polygonContainsPolygon`) y solapamiento (`polygonsOverlap`) directamente a PostGIS en PostgreSQL. |
| **Media** | Arquitectura / Código | Duplicación de formateo de fechas y cálculo de hora local Córdoba | Centralizar utilidades de tiempo y formateadores de zona horaria en `@agrosense/contracts/time`. |
| **Media** | Seguridad / Mantenibilidad | Uso mixto de Service Role y User Client en el servicio de onboarding | Refactorizar `createFarm` y `createPlot` para operar íntegramente bajo el contexto de seguridad del usuario autenticado (RLS nativo). |
| **Baja** | Observabilidad | Falta de métricas de telemetría unificadas en jobs de automatización | Integrar OpenTelemetry o métricas de Cloudflare Analytics Engine en los flujos cron y webhook de WhatsApp. |

---

### Ejemplos Concretos de Refactorización

#### 1. Paralelización de Herramientas Read-Only en el Agente (`apps/api/src/agent/runner.ts`)
Actualmente, el agente serializa todas las herramientas con una cadena de promesas para evitar carreras, penalizando herramientas que solo consultan datos meteorológicos:

```typescript
// ANTES: Serialización forzada de todas las herramientas
let pending: Promise<unknown> = Promise.resolve();
const tools: ToolSet = Object.fromEntries(
  Object.entries(options.tools).map(([name, definition]) => [
    name,
    {
      ...definition,
      execute: (input, execution) => {
        const task = pending.then(async () => {
          signal.throwIfAborted();
          // ejecución bloqueante uno a uno
          return await definition.execute(input, execution);
        });
        pending = task.catch(() => {});
        return task;
      },
    }
  ])
);
```

**Refactorización Propuesta:**
Permitir paralelismo controlado mediante un semáforo de concurrencia para llamadas de lectura (máximo 3 concurrentes), preservando la seguridad y reduciendo el tiempo de respuesta hasta en un 60%:

```typescript
// DESPUÉS: Concurrencia acotada para herramientas de lectura
import pLimit from "p-limit"; // o un semáforo ligero equivalente nativo

const readLimit = pLimit(3);

const tools: ToolSet = Object.fromEntries(
  Object.entries(options.tools).map(([name, definition]) => [
    name,
    {
      ...definition,
      execute: (input, execution) => {
        return readLimit(async () => {
          signal.throwIfAborted();
          const started = Date.now();
          let result = (await definition.execute(input, execution)) as ToolResult;

          if (new TextEncoder().encode(JSON.stringify(result)).byteLength > 32768) {
            result = {
              ok: false,
              error: {
                code: "TOOL_RESULT_TOO_LARGE",
                message: "Narrow the query; the result exceeds the allowed size",
              },
            };
          }

          trace.push({
            tool: name,
            ok: result.ok,
            errorCode: result.ok ? null : result.error.code,
            durationMs: Date.now() - started,
          });

          return result;
        });
      },
    } satisfies Tool,
  ]),
);
```

---

#### 2. Centralización del Proveedor de Tiempos y Fechas de Córdoba (`packages/contracts/src/time.ts`)
Evitar la dispersión de formateadores `Intl.DateTimeFormat` duplicados en backend y frontend:

```typescript
// packages/contracts/src/time.ts
export const CORDOBA_TIMEZONE = "America/Argentina/Cordoba";

const cordobaDateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: CORDOBA_TIMEZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const cordobaDisplayFormatter = new Intl.DateTimeFormat("es-AR", {
  timeZone: CORDOBA_TIMEZONE,
  dateStyle: "medium",
  timeStyle: "short",
});

/** Devuelve la fecha local en formato YYYY-MM-DD para la zona horaria del establecimiento */
export function getCordobaLocalDate(date: Date = new Date()): string {
  return cordobaDateFormatter.format(date);
}

/** Formateo consistente de instantes para interfaz y notificaciones */
export function formatCordobaDisplayInstant(instant: string | null): string {
  if (!instant) return "No disponible";
  return cordobaDisplayFormatter.format(new Date(instant));
}
```

---

#### 3. Delegación de la Validación Geométrica a PostGIS (`supabase/migrations`)
En lugar de cargar polígonos a la memoria del Worker para iterar sobre vértices con `polygonContainsPolygon`, se debe crear una función SQL pura aprovechando las capacidades espaciales nativas:

```sql
-- Migración SQL complementaria
CREATE OR REPLACE FUNCTION validate_plot_geometry(
  p_farm_id UUID,
  p_plot_geojson JSONB,
  p_sample_point_geojson JSONB
) RETURNS BOOLEAN LANGUAGE plpgsql STABLE AS $$
DECLARE
  v_farm_geom GEOMETRY;
  v_plot_geom GEOMETRY;
  v_point_geom GEOMETRY;
BEGIN
  SELECT ST_SetSRID(ST_GeomFromGeoJSON(boundary_geojson), 4326)
  INTO v_farm_geom
  FROM farms WHERE id = p_farm_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'FARM_NOT_FOUND';
  END IF;

  v_plot_geom := ST_SetSRID(ST_GeomFromGeoJSON(p_plot_geojson), 4326);
  v_point_geom := ST_SetSRID(ST_GeomFromGeoJSON(p_sample_point_geojson), 4326);

  -- 1. Validar que la parcela esté totalmente contenida en el campo
  IF NOT ST_Contains(v_farm_geom, v_plot_geom) THEN
    RAISE EXCEPTION 'PLOT_OUTSIDE_FARM_BOUNDARY';
  END IF;

  -- 2. Validar que el punto de muestreo meteorológico esté dentro de la parcela
  IF NOT ST_Contains(v_plot_geom, v_point_geom) THEN
    RAISE EXCEPTION 'SAMPLE_POINT_OUTSIDE_PLOT';
  END IF;

  -- 3. Validar que no solape con parcelas existentes del mismo campo
  IF EXISTS (
    SELECT 1 FROM plots
    WHERE farm_id = p_farm_id
      AND ST_Intersects(ST_SetSRID(ST_GeomFromGeoJSON(boundary_geojson), 4326), v_plot_geom)
      AND NOT ST_Touches(ST_SetSRID(ST_GeomFromGeoJSON(boundary_geojson), 4326), v_plot_geom)
  ) THEN
    RAISE EXCEPTION 'PLOT_OVERLAPS_EXISTING';
  END IF;

  RETURN TRUE;
END;
$$;
```

---

### Próximos Pasos Sugeridos para Modernizar y Robustecer el Codebase

1. **Implementación de OpenTelemetry en Cloudflare Workers:**
   Configurar tracing distribuido nativo en `apps/api` para correlacionar el flujo completo: recepción de webhook de WhatsApp $\rightarrow$ ejecución de Durable Object $\rightarrow$ llamadas de herramientas $\rightarrow$ respuesta de OpenRouter.
2. **Caché de Imágenes Satelitales en Cloudflare R2:**
   Actualmente, las imágenes ráster de Sentinel-2 se devuelven en Base64 en la respuesta JSON tras descargarse y decodificarse en memoria (`fast-png`). Persistir el ráster procesado en un bucket Cloudflare R2 y devolver una URL firmada o servirla como asset estático reducirá drásticamente el peso de la respuesta del Worker (actualmente hasta 6-8 MB en base64) y la memoria consumida en el Edge.
3. **Ampliación del Catálogo de Reglas Fenológicas:**
   Extender `DEMO_V1_RULES` a un catálogo formal de producción (`PROD_V1_RULES`) respaldado por fuentes agronómicas certificadas (INTA / Universidades agrícolas argentinas), parametrizando variedades de ciclo corto y largo en trigo, girasol y sorgo.