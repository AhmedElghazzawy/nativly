// Re-exports of the API's response/request shapes, generated from its OpenAPI schema
// (`npm run gen:api`). Never hand-write these: regenerate when the API changes.
import type { components } from "@/lib/api-schema";

type Schemas = components["schemas"];

export type TokenPair = Schemas["TokenPair"];
export type User = Schemas["UserRead"];
export type CourseSummary = Schemas["CourseSummary"];
export type CourseDetail = Schemas["CourseDetail"];
export type LessonDetail = Schemas["LessonDetail"];
export type Step = Schemas["StepRead"];
export type McqExercise = Schemas["McqPublic"];
export type ClozeExercise = Schemas["ClozePublic"];
export type ReorderExercise = Schemas["ReorderPublic"];
export type Exercise = McqExercise | ClozeExercise | ReorderExercise;
export type ExerciseResponse =
  Schemas["McqResponse"] | Schemas["ClozeResponse"] | Schemas["ReorderResponse"];
export type AttemptResult = Schemas["AttemptResult"];
export type LessonProgress = Schemas["LessonProgressRead"];
export type Progress = Schemas["ProgressRead"];
export type DeckSummary = Schemas["DeckSummary"];
export type DeckDetail = Schemas["DeckDetail"];
export type DeckWord = Schemas["DeckWord"];
export type Word = Schemas["WordRead"];
export type QueueCard = Schemas["QueueCard"];
export type ReviewResult = Schemas["ReviewResult"];
export type ReviewSummary = Schemas["ReviewSummary"];
export type RatingName = Schemas["ReviewRequest"]["rating"];
export type WritingTask = Schemas["WritingTaskPublic"];
export type WritingSubmission = Schemas["SubmissionRead"];
export type WritingFeedback = Schemas["WritingFeedback"];
export type Mistake = Schemas["MistakeRead"];
