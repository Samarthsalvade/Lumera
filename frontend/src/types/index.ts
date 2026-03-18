export interface User {
  id: number;
  email: string;
  username: string;
  created_at: string;
}

export interface Analysis {
  id: number;
  user_id: number;
  image_path: string;
  skin_type: string;
  confidence: number;
  recommendations: string;        // JSON string or array — parsed in component
  created_at: string;
  // ── new fields from the updated backend ──
  normalized_image_b64?: string;         // base64 PNG of the cropped face
  face_detection_confidence?: number;    // 0–100
  message?: string;
}

export interface AuthResponse {
  message: string;
  access_token: string;
  user: User;
}

export interface AnalysisResponse {
  success: boolean;
  message: string;
  analysis: Analysis;
}