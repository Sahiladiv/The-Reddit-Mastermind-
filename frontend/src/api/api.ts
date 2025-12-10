import axios from "axios";

const API = axios.create({
  baseURL: "http://the-reddit-mastermind.onrender.com/",
});

// Types for FastAPI responses
export interface RedditPost {
  post_id: string;
  subreddit: string;
  author: string;
  title: string;
  body: string;
  query: string;
}

export interface RedditComment {
  comment_id: string;
  post_id: string;
  parent_comment_id: string | null;
  author: string;
  text: string;
}

export interface CalendarEntry {
  date: string;
  subreddit: string;
  post: RedditPost;
  comments: RedditComment[];
}

// API Calls

export const generateWeek = async (payload: {
  max_comments_per_thread: number;
  start_date?: string;
  override_posts_per_week?: number;
}) => {
  return API.post<CalendarEntry[]>("/generate-week", payload);
};

export const generateWeeksAndSave = async (payload: {
  num_weeks: number;
  output_dir: string;
  max_comments_per_thread: number;
}) => {
  return API.post<{
    status: string;
    weeks_generated: number;
    files: string[];
  }>("/generate-weeks-and-save", payload);
};
