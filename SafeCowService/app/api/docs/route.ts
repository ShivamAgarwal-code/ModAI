import { NextResponse } from 'next/server'
import { readFileSync } from 'fs'
import { join } from 'path'
import { load } from 'js-yaml'

export async function GET() {
  try {
    const swaggerYaml = readFileSync(join(process.cwd(), 'openapi.yaml'), 'utf8')
    const swaggerJson = load(swaggerYaml)
    
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SafeCow Service API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
    <script>
        window.onload = () => {
            window.ui = SwaggerUIBundle({
                spec: ${JSON.stringify(swaggerJson)},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
            })
        }
    </script>
</body>
</html>`

    return new NextResponse(html, {
      headers: {
        'Content-Type': 'text/html',
      },
    })
  } catch (error) {
    console.error('Failed to serve API documentation:', error)
    return new NextResponse('Internal Server Error', { status: 500 })
  }
} 