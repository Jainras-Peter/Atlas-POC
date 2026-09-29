import type { Customer } from "../types";

export async function fetchUsers(): Promise<Customer[]> {
  const response = await fetch("/api/users");
  if (!response.ok) throw new Error("Failed to load users");
  return response.json();
}

export async function fetchUser(id: string): Promise<Customer> {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) throw new Error("User not found");
  return response.json();
}
