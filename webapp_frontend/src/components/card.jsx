export function Card({ house }) {
	return (
		<div className='card'>
			<div className='image-container'>
				<img
					src={house.image_url || '/houses/house.png'}
					alt={house.name}
					className='house-photo'
				/>
				<div className='info-overlay'>
					<div className='info-item'>Площадь: {house.area} м²</div>
					<div className='info-item'>Размер: {house.house_size}</div>
					<div className='info-item'>Этажей: {house.floors}</div>
				</div>
			</div>
			<h5 className='card-label'>{house.name}</h5>
		</div>
	)
}
