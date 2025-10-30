import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { getHouseDetails } from '../services/api/apiServices'
import './HouseInfo.css'

export function HouseInfo() {
	const location = useLocation()
	const { id } = location.state || {}
	const [houseData, setHouseData] = useState(null)

	useEffect(() => {
		if (id) {
			getHouseDetails(id)
				.then(data => {
					if (data.house) {
						setHouseData(data.house)
					} else {
						setHouseData(null)
					}
				})
				.catch(error => console.error('Ошибка загрузки данных дома:', error))
		}
	}, [id])

	if (!houseData) {
		return <p>Загрузка информации о доме...</p>
	}

	return (
		<div className='house-info'>
			<div className='image-container'>
				<img
					src={houseData.image_url || '/houses/house.png'}
					alt={houseData.name}
					className='house-image'
				/>
			</div>

			<h2 className='house-title'>{houseData.name}</h2>

			<div className='info-box'>
				<div className='info-item'>Площадь: {houseData.area} м²</div>
				<div className='info-item'>Размер: {houseData.house_size}</div>
				<div className='info-item'>Этажей: {houseData.floors}</div>
			</div>

			<div className='about-section'>
				<h3>О доме</h3>
				<p>{houseData.description || 'Описание отсутствует'}</p>
			</div>
		</div>
	)
}
