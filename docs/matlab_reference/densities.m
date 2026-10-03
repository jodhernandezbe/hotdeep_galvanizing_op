
%% Densities of solutions
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 04 October, 2017
%%-----------------------------------------------------------------------------------------------------------

function density_solution = density(T,C,N)

% N is a number to indentify the process' step:
% (1) Degreasing
% (2) Pickling

% T is the step's temperature [oC]
% C is the setp's concentration [ % wt]

if N == 1

rho_1d_aux = -0.0114*(T - 40)/20 + 1.1645; % Density of NaOH solution at 16 % and T [g/cm3]
rho_1i_aux = -0.0092*(T - 40)/20 + 1.0033; % Density of NaOH solution at 1 % and T [g/cm3]
rho_NaOH = (rho_1d_aux - rho_1i_aux)*(C - 1)/15 ... % Density of NaOH solution at C and T [g/cm3]
+ rho_1i_aux;
density_solution = rho_NaOH*1000; % Density of NaOH solution at C and T [kg/m3]

elseif N == 2

rho_1d_aux = -0.0130*(T - 10)/30 + 1.0920; % Density of HCl solution at 18 % and T [g/cm3]
rho_1i_aux = -0.0078*(T - 10)/30 + 1.0048; % Density of HCl solution at 1 % and T [g/cm3]
rho_HCl = (rho_1d_aux - rho_1i_aux)*(C - 1)/16 ... % Density of HCl solution at C and T [g/cm3]
+ rho_1i_aux;
density_solution = rho_HCl*1000; % Density of HCl solution at C and T [kg/m3

end

return
