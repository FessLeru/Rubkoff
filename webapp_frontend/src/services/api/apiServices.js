import { USER_ID } from '../../constants/telegram'
import apiClient from './apiClient'

export const getAllHouses = async (limit, page) => {
	try {
		const response = await apiClient.get(`houses/?page=${page}&limit=${limit}`)
		return response.data
	} catch (error) {
		console.error('Error fetching data:', error)
		throw error
	}
}

export const getHouseDetails = async houseId => {
	try {
		const response = await apiClient.get(`/houses/${houseId}`)
		return response.data
	} catch (error) {
		console.error('Error fetching data:', error)
		throw error
	}
}

export const getHouseAIRecommendations = async () => {
	try {
		const response = await apiClient.get(`/user/${USER_ID}/recommendations`)
		return response.data
	} catch (error) {
		console.error('Error fetching data:', error)
		throw error
	}
}
