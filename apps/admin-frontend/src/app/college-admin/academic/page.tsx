"use client";

import { useEffect, useState } from "react";
import { adminApiRequest } from "@/lib/api-client";

type Course = { id: string; course_name: string; course_abbreviation?: string; course_category: string; active_status: boolean; verification_status: string };

export default function AcademicCataloguePage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("ENGINEERING");
  const [fees, setFees] = useState<any[]>([]);
  const [feeCourse, setFeeCourse] = useState("");
  const [semester, setSemester] = useState("1");
  const [amount, setAmount] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [error, setError] = useState("");
  const load = async () => {
    const result = await adminApiRequest<Course[]>("/college-admin/academic/courses");
    if (result.success && result.data) setCourses(result.data);
    else setError(result.error || "Could not load catalogue.");
    const feeResult = await adminApiRequest<any[]>("/college-admin/academic/fees");
    if (feeResult.success && feeResult.data) setFees(feeResult.data);
  };
  const addFee = async (event: React.FormEvent) => {
    event.preventDefault(); setError("");
    const result = await adminApiRequest("/college-admin/academic/fees", { method: "POST", body: JSON.stringify({ course_id: feeCourse, semester_number: Number(semester), fee_amount: Number(amount), academic_year: academicYear || null, fee_type: "SEMESTER", verification_status: "PENDING" }) });
    if (!result.success) { setError(result.error || "Could not save fee."); return; }
    setAmount(""); await load();
  };
  const approveCourse = async (course: Course) => {
    const result = await adminApiRequest(`/college-admin/academic/courses/${course.id}`, { method: "PATCH", body: JSON.stringify({ course_name: course.course_name, course_abbreviation: course.course_abbreviation, course_category: course.course_category, active_status: true, verification_status: "APPROVED" }) });
    if (result.success) await load(); else setError(result.error || "Could not approve course.");
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
    <section className="overflow-x-auto rounded-xl border"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-3">Course</th><th className="p-3">Category</th><th className="p-3">Availability</th><th className="p-3">Verification</th><th className="p-3">Action</th></tr></thead><tbody>{courses.map(course => <tr key={course.id} className="border-b last:border-0"><td className="p-3 font-medium">{course.course_name}</td><td className="p-3">{course.course_category}</td><td className="p-3">{course.active_status ? "Active" : "Inactive"}</td><td className="p-3">{course.verification_status}</td><td className="p-3">{!(course.active_status && course.verification_status === "APPROVED") && <button onClick={() => approveCourse(course)} className="text-indigo-500">Verify & publish</button>}</td></tr>)}</tbody></table></section>
    <form onSubmit={addFee} className="rounded-xl border p-4 space-y-3"><h2 className="font-semibold">Add semester fee</h2><div className="flex flex-wrap gap-3"><select required value={feeCourse} onChange={e => setFeeCourse(e.target.value)} className="rounded-lg border bg-transparent px-3 py-2"><option value="">Select course</option>{courses.map(c => <option key={c.id} value={c.id}>{c.course_name}</option>)}</select><input required type="number" min="1" max="16" value={semester} onChange={e => setSemester(e.target.value)} className="w-24 rounded-lg border bg-transparent px-3 py-2" aria-label="Semester number"/><input required type="number" min="0" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} placeholder="Fee amount (INR)" className="w-48 rounded-lg border bg-transparent px-3 py-2"/><input value={academicYear} onChange={e => setAcademicYear(e.target.value)} placeholder="Academic year (optional)" className="rounded-lg border bg-transparent px-3 py-2"/><button className="rounded-lg bg-indigo-600 px-4 py-2 text-white">Save pending fee</button></div></form>
    <section className="rounded-xl border p-4"><h2 className="font-semibold mb-3">Fee schedules</h2>{fees.length ? <ul className="space-y-2 text-sm">{fees.map(f => <li key={f.id}>{courses.find(c => c.id === f.course_id)?.course_name || "Course"} · Semester {f.semester_number} · {f.currency} {f.fee_amount} · {f.academic_year || "Year not set"} · {f.verification_status}</li>)}</ul> : <p className="text-sm text-gray-500">No fee schedules added.</p>}</section>
    <p className="text-xs text-gray-500">Fees begin pending and are not shown as verified to students until an authorized administrator confirms them.</p>
  </main>;
}
