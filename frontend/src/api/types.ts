export type Role = "admin" | "teacher" | "student" | "parent";

export interface AuthSession {
  access_token: string;
  token_type: string;
  role: Role;
  user_id: number;
  full_name: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface SchoolClass {
  id: number;
  name: string;
  academic_year: string;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  class_id: number;
  teacher_id: number | null;
}

export interface Student {
  id: number;
  roll_number: string;
  class_id: number | null;
  date_of_birth: string | null;
  user: CurrentUser;
}

export interface SubjectPerformance {
  subject_id: number;
  subject_name: string;
  average_percentage: number;
  assessments_count: number;
  trend: string;
}

export interface StudentMetrics {
  student_id: number;
  student_name: string;
  attendance_rate: number;
  sessions_recorded: number;
  overall_average: number;
  marks_trend: string;
  trend_delta: number;
  assignment_completion_rate: number;
  missing_assignments: number;
  subject_performance: SubjectPerformance[];
  weakest_subjects: string[];
  strongest_subjects: string[];
  risk_score: number;
  risk_level: string;
  risk_reasons: string[];
}

export interface StudentInsight {
  metrics: StudentMetrics;
  summary: string;
  recommendations: string[];
  source: string;
  generated_at: string;
}

export interface AtRiskStudent {
  student_id: number;
  student_name: string;
  class_id: number | null;
  risk_score: number;
  risk_level: string;
  risk_reasons: string[];
  attendance_rate: number;
  overall_average: number;
}

export interface ClassAnalytics {
  class_id: number;
  class_name: string;
  students_count: number;
  average_attendance: number;
  average_score: number;
  at_risk_count: number;
  subject_averages: SubjectPerformance[];
  top_performers: AtRiskStudent[];
  students_needing_support: AtRiskStudent[];
}

export interface AttendanceRecord {
  id: number;
  student_id: number;
  subject_id: number | null;
  session_date: string;
  status: "present" | "absent" | "late" | "excused";
}

export interface Mark {
  id: number;
  assessment_id: number;
  student_id: number;
  score: number;
  remarks: string | null;
}

export interface Assessment {
  id: number;
  subject_id: number;
  title: string;
  assessment_type: string;
  max_score: number;
  held_on: string;
}

export interface Assignment {
  id: number;
  subject_id: number;
  title: string;
  description: string | null;
  max_score: number;
  due_date: string;
}

export interface Submission {
  id: number;
  assignment_id: number;
  student_id: number;
  status: string;
  submitted_on: string | null;
  score: number | null;
  feedback: string | null;
}
