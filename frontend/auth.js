import {
  getCandidateSession,
  clearClientBootstrap,
  linkGoogleCandidate,
  loginCandidate,
  logoutCandidate,
  signupCandidate,
} from "./api.js";

let snapshot = { authenticated: false, candidate: null, membership: null };
let hasLoadedCandidate = false;
let authGeneration = 0;

export function authState() { return snapshot; }
export function candidate() {
  if (!snapshot.candidate) return null;
  const tier = snapshot.membership?.tier || "free";
  const planCode = snapshot.membership?.plan_code || "free";
  const planName = snapshot.membership?.plan?.name || (tier === "premium" ? "Premium" : "Free");
  return {
    ...snapshot.candidate,
    membership: snapshot.membership,
    plan: planName,
    plan_code: planCode,
    entitlement_version: snapshot.membership?.entitlement_version ?? 0,
    sign_in_methods: snapshot.candidate?.sign_in_methods || ["email"],
    is_premium: tier === "premium" && snapshot.membership?.status === "active",
  };
}
export function membership() { return snapshot.membership; }
export function candidateLoaded() { return hasLoadedCandidate; }

function publish(next) {
  snapshot = { ...snapshot, ...next };
  window.dispatchEvent(new CustomEvent("candidate-change", { detail: snapshot }));
  return snapshot;
}

function beginAuthMutation() {
  authGeneration += 1;
}

export async function refreshCandidate({ notify = false } = {}) {
  // Authorization can change outside this page (for example, a controlled
  // founder promotion). A refresh must therefore bypass the bootstrap cache.
  const generation = authGeneration;
  const next = await getCandidateSession({ force: true });
  if (generation !== authGeneration) return snapshot;
  hasLoadedCandidate = true;
  if (notify) return publish(next);
  snapshot = { ...snapshot, ...next };
  return snapshot;
}

export async function signUp(payload) {
  beginAuthMutation();
  clearClientBootstrap("candidate", "readiness");
  const result = await signupCandidate(payload);
  hasLoadedCandidate = true;
  return publish(result);
}

export async function logIn(payload) {
  beginAuthMutation();
  clearClientBootstrap("candidate", "readiness");
  const result = await loginCandidate(payload);
  hasLoadedCandidate = true;
  return publish(result);
}

export async function linkGoogle(password) {
  beginAuthMutation();
  clearClientBootstrap("candidate", "readiness");
  const result = await linkGoogleCandidate(password);
  hasLoadedCandidate = true;
  return publish(result);
}

export async function logOut() {
  beginAuthMutation();
  await logoutCandidate();
  clearClientBootstrap("candidate", "readiness");
  hasLoadedCandidate = true;
  return publish({ authenticated: false, candidate: null, membership: null });
}
