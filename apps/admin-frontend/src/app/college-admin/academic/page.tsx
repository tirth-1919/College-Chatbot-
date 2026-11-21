"use client";

import { useEffect, useState } from "react";
import { adminApiRequest } from "@/lib/api-client";

type Course = { id: string; course_name: string; course_abbreviation?: string; course_category: string; active_status: boolean; verification_status: string };

export default function AcademicCataloguePage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("ENGINEERING");
  const [error, setError] = useState("");
  const load = async () => {
    const result = await adminApiRequest<Course[]>("/college-admin/academic/courses");
    if (result.success && result.data) setCourses(result.data);
    else setError(result.error || "Could not load catalogue.");
  };
  useEffect(() => { void load(); }, []);
  const addCourse = async (event: React.FormEvent) => {
    event.preventDefault(); setError("");
    const result = await adminApiRequest("/college-admin/academic/courses", { method: "POST", body: JSON.stringify({ course_name: name, course_category: category }) });
    if (!result.success) { setError(result.error || "Could not save course."); return; }
    setName(""); await load();
  };
  return <main className="max-w-5xl mx-auto p-6 space-y-6">
    <header><h1 className="text-2xl font-semibold">Courses & Fees</h1><p className="text-sm text-gray-500 mt-1">Only courses registered and approved for your college appear in student answers.</p></header>
    <form onSubmit={addCourse} className="rounded-xl border p-4 flex flex-wrap gap-3">
      <input className="min-w-56 flex-1 rounded-lg border bg-transparent px-3 py-2" value={name} onChange={e => setName(e.target.value)} placeholder="Course or branch name" required />
      <select className="rounded-lg border bg-transparent px-3 py-2" value={category} onChange={e => setCategory(e.target.value)}><option>ENGINEERING</option><option>DIPLOMA</option><option>COMPUTER_APPLICATIONS</option><option>POSTGRADUATE</option><option>SCIENCE</option><option>OTHER</option></select>
      <button className="rounded-lg bg-indigo-600 px-4 py-2 text-white">Add course</button>
    </form>
    {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
    <section className="overflow-x-auto rounded-xl border"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-3">Course</th><th className="p-3">Category</th><th className="p-3">Availability</th><th className="p-3">Verification</th></tr></thead><tbody>{courses.map(course => <tr key={course.id} className="border-b last:border-0"><td className="p-3 font-medium">{course.course_name}</td><td className="p-3">{course.course_category}</td><td className="p-3">{course.active_status ? "Active" : "Inactive"}</td><td className="p-3">{course.verification_status}</td></tr>)}</tbody></table></section>
    <p className="text-xs text-gray-500">New entries start inactive and pending. Fee schedules and verification controls are available through the secured academic API.</p>
  </main>;
}
