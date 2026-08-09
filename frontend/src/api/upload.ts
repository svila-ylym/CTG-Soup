import http from './http'
import type { UploadedAsset, UploadImageResult } from '@/types'

export const uploadApi = {
  images() {
    return http.get<UploadedAsset[]>('/uploads/images')
  },

  image(file: File) {
    const form = new FormData()
    form.append('file', file)
    return http.post<UploadImageResult>('/uploads/images', form)
  },
}
