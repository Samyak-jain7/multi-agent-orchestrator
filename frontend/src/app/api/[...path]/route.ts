import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_BACKEND_URL || 'http://localhost:8000';
const API_KEY = process.env.API_KEY || 'your-secure-app-api-key-here';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const search = request.nextUrl.search;

  const url = `${BACKEND_URL}/api/v1/${path}${search}`;

  // For streaming endpoints, return the response as a stream
  if (path.includes('stream')) {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'X-API-Key': API_KEY,
      },
    });

    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }

  // Regular GET
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
  });

  const data = await response.json().catch(() => null);
  return NextResponse.json(data, { status: response.status });
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const body = await request.json();

  const url = `${BACKEND_URL}/api/v1/${path}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => null);
  return NextResponse.json(data, { status: response.status });
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const body = await request.json();

  const url = `${BACKEND_URL}/api/v1/${path}`;

  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => null);
  return NextResponse.json(data, { status: response.status });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');

  const url = `${BACKEND_URL}/api/v1/${path}`;

  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
  });

  const data = await response.json().catch(() => null);
  return NextResponse.json(data, { status: response.status });
}
