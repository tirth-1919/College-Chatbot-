import { apiRequest } from "@/lib/api-client";
import { College } from "@/types/college";

export const collegeService = {
  async getColleges(onlyApproved: boolean = true) {
    return apiRequest<College[]>(`/colleges${onlyApproved ? "" : "?all_colleges=true"}`);
  },

  async getCollegeByIdOrSlug(idOrSlug: string) {
    return apiRequest<College>(`/colleges/${idOrSlug}`);
  },
};

