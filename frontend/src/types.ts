export interface StructuredScore {
  structured_score: number;
  skill_score: number;
  career_score: number;
  exp_score: number;
  edu_score: number;
  loc_score: number;
  must_have_skill_count: number;
  matched_skills: string[];
}

export interface BehavioralScore {
  behavioral_score: number;
  open_to_work: number;
  activity_score: number;
  inactive_days: number;
  response_rate: number;
  interview_completion: number;
  notice_days: number;
  github_score: number;
  trust_score: number;
  demand_score: number;
}

export interface CandidateResult {
  candidate_id: string;
  rank: number;
  display_score: number;
  name: string;
  headline: string;
  current_title: string;
  years_of_experience: number;
  location: string;
  current_company: string;
  current_industry: string;
  current_company_size: string;
  semantic_score: number;
  structured: StructuredScore;
  behavioral: BehavioralScore;
  honeypot_penalty: number;
  honeypot_flags: string[];
  reasoning: string;
}

export interface RankResponse {
  total_candidates: number;
  top_n: number;
  honeypots_in_top: number;
  top_score: number;
  results: CandidateResult[];
}

export interface RankRequest {
  data_path: string;
  is_sample: boolean;
  top_n: number;
  use_llm: boolean;
  llm_n: number;
  coarse_n: number;
}

export interface JobDescription {
  raw_text: string;
  must_have_skills: string[];
  nice_to_have_skills: string[];
  [key: string]: unknown;
}
