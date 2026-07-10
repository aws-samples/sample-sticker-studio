"use server";

import { getSessionToken } from "@/lib/auth";

interface GenerateDescription {
  character: string;
  activity: string;
  location: string;
}

interface GenerateResult {
  presignedUrls: string[];
  error?: never;
}

interface GenerateError {
  error: string;
  presignedUrls?: never;
}

export async function generateSticker(
  description: GenerateDescription,
): Promise<GenerateResult | GenerateError> {
  const token = await getSessionToken();
  if (!token) {
    return { error: "Not authenticated" };
  }

  const apiEndpoint = process.env.NEXT_PUBLIC_API_URL ?? "";

  try {
    const response = await fetch(`${apiEndpoint}/generateImages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(description),
    });

    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(`Backend returned ${response.status}: ${body}`);
    }

    const data = await response.json();
    return { presignedUrls: data.presigned };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Image generation failed";
    return { error: message };
  }
}
