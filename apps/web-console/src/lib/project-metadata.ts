export const projectPhase = "Phase 6 / Security and operational hardening";

export const localPersonas = [
  { label: "Requester", token: "local-requester-token" },
  { label: "Reviewer", token: "local-reviewer-token" },
  { label: "Operator", token: "local-operator-token" },
  { label: "Administrator", token: "local-administrator-token" },
] as const;

export const dataProfiles = [
  { label: "General content", category: "general_content" },
  { label: "Contact information", category: "contact_information" },
  { label: "Health information", category: "health_information" },
  { label: "Financial information", category: "financial_information" },
] as const;

export const approvalPersonas = [
  { label: "Reviewer", token: "local-reviewer-token" },
  { label: "Administrator", token: "local-administrator-token" },
] as const;

export const localOperatorToken = "local-operator-token";
